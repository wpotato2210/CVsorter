# Firmware Lifecycle Specification (v3)

## 1) Bootloader Responsibilities and Immutable Root-of-Trust Assumptions

### 1.1 Immutable Root of Trust (RoT)
The platform shall define a minimal immutable code and data region (ROM, OTP, eFuse-backed metadata, or equivalent) that establishes the hardware root of trust.

**RoT assumptions:**
- Public key material (or hash of a root signing key/certificate) used to validate first mutable boot stage is immutable after manufacturing except through explicitly supported secure provisioning flow.
- Device identity (unique device ID and provisioning state) is bound to hardware and not modifiable by runtime firmware.
- Secure debug configuration (enabled/disabled state, authenticated debug requirements) is latched at boot from immutable policy.
- Anti-rollback reference (monotonic counter anchor, OTP floor version, or secure element counter) is trusted and cannot be decremented by software.

### 1.2 Bootloader Responsibilities
The bootloader is responsible for all early-chain security and controlled transition to application firmware.

**Required responsibilities:**
1. **Hardware initialization (minimal):** initialize clocks, memory, and cryptographic primitives required for image verification.
2. **Boot chain verification:** verify firmware metadata, signature, version constraints, and integrity before execution.
3. **Slot selection:** support A/B (or equivalent dual-bank) image selection and fallback decision logic.
4. **State enforcement:** honor lifecycle states (manufacturing, field, recovery, decommissioned) and allow only permitted boot targets per state.
5. **Tamper/failure response:** increment boot-failure counters and enter recovery mode after policy-defined thresholds.
6. **Measured boot export (if supported):** emit hash measurements to secure log/registers for later attestation.
7. **Handoff contract:** pass verified image metadata, boot reason, rollback index, and last-reset cause to runtime firmware.

### 1.3 Security Boundaries
- Bootloader update path must be stricter than application OTA (e.g., dedicated signer, explicit maintenance mode, tighter quorum approval).
- Runtime firmware must not be able to alter verification policy, trust anchors, or anti-rollback state except through authenticated privileged services.

---

## 2) Secure Boot Verification Steps and Key/Certificate Rotation Policy

### 2.1 Verification Flow
On each reset, secure boot shall execute the following steps in order:

1. **Read immutable trust anchors** from RoT region.
2. **Select candidate image slot** according to boot policy (prefer pending verified upgrade, else current active).
3. **Parse signed manifest** containing:
   - Image digest,
   - Firmware semantic version,
   - Security patch level,
   - Build ID,
   - Allowed hardware compatibility range,
   - Signer certificate chain metadata,
   - Expiration/revocation indicators.
4. **Validate certificate chain** from image signer certificate to pinned root/intermediate trust anchor.
5. **Check revocation status** against local denylist/CRL snapshot (or stapled revocation statement in offline deployments).
6. **Verify signature** over manifest and image digest.
7. **Verify image integrity** by hashing image and comparing to manifest digest.
8. **Enforce anti-rollback policy** (version and security counter must be >= stored floor).
9. **Enforce compatibility policy** (board ID, MCU stepping, required feature bits).
10. **Mark image bootable** and transfer control.

If any step fails, bootloader shall reject the image, log the failure reason, and attempt fallback slot. If no valid image remains, enter recovery mode.

### 2.2 Key and Certificate Rotation Policy
**Key hierarchy:**
- Root CA key: long-lived, offline, emergency-only use.
- Intermediate release-signing key(s): medium-lived, controlled online HSM use.
- Optional role-based signers: bootloader signer and application signer are separate.

**Rotation requirements:**
- Support at least **N+1 trust anchor overlap** (new key accepted before old key removal).
- New trust anchors are delivered in signed trust-bundle updates verified by currently trusted chain.
- Rotation window must include:
  1. Introduce new intermediate/root hash as trusted,
  2. Start signing releases with new key,
  3. Observe fleet adoption threshold,
  4. Revoke old key and prune at next maintenance release.
- Emergency key compromise response:
  - Add compromised key ID to revocation list,
  - Force rollout signed by emergency signer,
  - Optionally require recovery-mode revalidation for affected devices.

**Validity constraints:**
- Device clock-independent validity checks should rely on monotonic counters or signed epochs if RTC trust is weak.
- Certificate expiry tolerance in disconnected environments must be bounded by policy and accompanied by signed epoch updates.

---

## 3) OTA Update Protocol (Staged Rollout, Health Checks, Automatic Rollback)

### 3.1 OTA Package Model
Each OTA artifact shall include:
- Signed manifest,
- Firmware payload (full image or delta),
- Dependency metadata (minimum bootloader/runtime versions),
- Migration hooks schema version,
- Post-install health criteria and rollback timeout.

### 3.2 OTA State Machine
1. **Download:** retrieve package over authenticated channel (mTLS or signed request tokens).
2. **Pre-verify:** signature/integrity checks before write.
3. **Install to inactive slot:** never overwrite active running slot.
4. **Mark pending:** bootloader flag set for trial boot.
5. **Trial boot:** new image gets bounded probation window.
6. **Health evaluation:** runtime emits pass/fail attestation.
7. **Commit or rollback:** commit on success, otherwise revert automatically.

### 3.3 Staged Rollout Policy
Rollouts shall proceed in rings with automated gates:
- **Ring 0 (internal/canary):** 1–5% of representative devices.
- **Ring 1 (early field):** 10–20% after Ring 0 passes SLOs.
- **Ring 2 (broad):** remaining fleet once error budgets remain within limits.

**Promotion gates (examples):**
- Boot success rate >= 99.5%,
- No critical safety faults attributable to update,
- Crash-loop incidence below threshold,
- Communication uptime within expected band.

Failure of any gate pauses rollout and opens incident workflow.

### 3.4 Health Checks
A trial image is healthy only if all required checks pass within probation window:
- Successful completion of initialization sequence,
- Stable main loop/scheduler heartbeat,
- Sensor and actuator self-tests pass,
- Control channel connectivity restored,
- No repeated watchdog resets,
- Safety interlocks operational.

Health report must be persisted atomically and signed/MACed if stored in mutable memory shared across resets.

### 3.5 Automatic Rollback Conditions
Rollback is mandatory when any of the following occurs during probation:
- Boot failure count exceeds configured threshold,
- Hard-fault/reset loop detected (e.g., >=3 resets in T minutes),
- Watchdog-triggered reset attributable to new image,
- Safety-critical task misses hard deadline repeatedly,
- Mandatory subsystem health check timeout,
- Explicit remote rollback directive signed by control plane.

After rollback, device records failing build ID, reason code, and suppresses reattempt until newer approved build is available (unless forced recovery command is provided).

---

## 4) Real-Time Scheduling Policy (Hard vs Soft Deadlines by Subsystem)

### 4.1 Scheduling Model
Firmware shall use fixed-priority preemptive scheduling (RTOS) with rate-monotonic assignment by default. Hard-deadline tasks must not be blocked by soft-deadline workloads.

### 4.2 Deadline Classes
- **Hard deadline:** miss is safety- or correctness-critical; requires immediate mitigation.
- **Soft deadline:** miss degrades performance/observability but does not immediately compromise safety.

### 4.3 Subsystem Deadline Matrix
| Subsystem | Example Tasks | Deadline Class | Typical Period | Miss Policy |
|---|---|---|---|---|
| Actuator control loop | PWM/torque/position update | Hard | 1–5 ms | Enter safe-output mode after configured consecutive misses |
| Safety monitoring | Interlock sampling, limit checks | Hard | 1–10 ms | Trigger safety state transition immediately |
| Watchdog service task | Aggregate subsystem heartbeats | Hard | 10–50 ms | Escalate reset tier |
| Communications RX/TX | Command handling, telemetry uplink | Soft (Hard for safety commands) | 10–100 ms | Drop non-critical frames; prioritize safety channel |
| State estimation | Sensor fusion/filter update | Soft/Hard by product profile | 5–20 ms | Degrade to fallback estimator or limp mode |
| Logging/diagnostics flush | Buffered event write/export | Soft | 100–1000 ms | Backpressure + bounded loss of low-priority logs |
| OTA/background maintenance | Download/verify chunks | Soft | opportunistic | Suspend during control load peaks |

### 4.4 Priority Inversion and Resource Control
- Use priority inheritance/ceiling on shared mutexes.
- Bound critical sections; avoid dynamic memory allocation in hard-deadline paths.
- Budget CPU utilization with admission control (e.g., hard tasks <= 70% sustained load).

---

## 5) Watchdog Hierarchy and Fault Escalation Policy (MCU, Comms, Actuator)

### 5.1 Hierarchical Watchdogs
1. **Task-level watchdogs:** per-critical-task heartbeat deadlines.
2. **Subsystem watchdogs:** MCU supervisor checks grouped heartbeats:
   - Core control subsystem,
   - Communications subsystem,
   - Actuation/safety subsystem.
3. **Hardware independent watchdog (IWDG/WDT):** final recovery mechanism reset by supervisor only when all critical subsystem heartbeats are valid.

### 5.2 Fault Escalation Levels
- **Level 0 (transient):** single missed heartbeat; log warning, no reset.
- **Level 1 (degraded):** repeated misses in one subsystem; restart affected service/task.
- **Level 2 (critical subsystem fault):** subsystem restart failed or hard deadline violations persist; transition to safe mode and reset application.
- **Level 3 (system fault):** repeated critical faults across reboot window; bootloader enters recovery slot or maintenance mode.
- **Level 4 (latched safety fault):** actuator or interlock violation; require explicit operator/service clearance before full function restore.

### 5.3 Subsystem-Specific Actions
- **MCU/control faults:** immediate safe-output command + application reset.
- **Comms faults:** retain local control autonomy, degrade remote features, continue safety supervision.
- **Actuator faults:** force neutral/disabled outputs, assert interlock, and prevent re-enable until diagnostics pass.

---

## 6) Structured Diagnostics/Logging Format, Retention, and Circular Buffer Behavior

### 6.1 Log Record Schema
Logs shall use structured, versioned records (binary TLV or JSON-lines equivalent). Minimum fields:
- `ts_monotonic_ms`
- `boot_id`
- `fw_version`
- `subsystem`
- `severity` (`DEBUG|INFO|WARN|ERROR|FATAL`)
- `event_code` (stable numeric identifier)
- `message_template_id`
- `kv` (bounded key-value payload)
- `reset_cause` (when applicable)
- `trace_id` (for multi-event correlation)

### 6.2 Retention Windows
- **High-severity events (ERROR/FATAL, safety/interlock):** retain minimum 30 days or last 10,000 records, whichever is larger.
- **Operational INFO/WARN:** retain minimum 7 days subject to storage budget.
- **DEBUG:** disabled by default in production; when enabled, strict short TTL and rate limiting.

### 6.3 Circular Buffer Policy
- Use fixed-size ring buffers per severity class to protect critical log retention from debug flooding.
- On overflow, overwrite oldest records **within same class** (never allow DEBUG to evict FATAL).
- Maintain watermark metrics and dropped-record counters.
- Persist crash snapshot region separately (last N seconds pre-reset) when supported.

### 6.4 Field Retrieval
- Retrieval interface shall support range queries by boot ID, timestamp window, severity, and event code.
- Export chunks must include sequence numbers and integrity tags for loss/corruption detection.
- Sensitive fields must be redacted or encrypted at rest/in transit according to deployment policy.

---

## 7) Emergency-Stop and Safety Interlock Integration Mapped to Firmware States

### 7.1 Firmware State Model
Minimum runtime states:
1. `BOOT_INIT`
2. `SELF_TEST`
3. `STANDBY`
4. `ACTIVE_CONTROL`
5. `DEGRADED`
6. `SAFE_STOP`
7. `RECOVERY`

### 7.2 E-Stop and Interlock Rules by State
| State | E-Stop Input | Safety Interlock Input | Required Firmware Behavior |
|---|---|---|---|
| `BOOT_INIT` | Monitored | Monitored | Do not enable actuators; fail closed on asserted signal |
| `SELF_TEST` | Monitored | Evaluated | Abort tests and enter `SAFE_STOP` if asserted/fail |
| `STANDBY` | Active | Active | Keep outputs disabled; only arm when interlocks healthy |
| `ACTIVE_CONTROL` | Active (highest priority) | Active | Immediate output inhibit + transition to `SAFE_STOP` on assert |
| `DEGRADED` | Active | Active | Restrict operation; assert interlock failure if worsening fault |
| `SAFE_STOP` | Latched | Latched | Maintain inhibited outputs until explicit reset procedure |
| `RECOVERY` | Active | Active | Permit limited diagnostics only; no actuator enable |

### 7.3 Signal Handling and Timing Requirements
- E-stop and hard interlock inputs must be sampled/latched in hard-deadline safety path.
- Debounce/filter windows must be bounded and safety-approved; emergency asserts bypass nonessential filtering.
- Maximum detection-to-output-inhibit latency shall be specified per product safety case and verified in hardware-in-loop testing.

### 7.4 Reset and Re-Enable Policy
Re-enable from `SAFE_STOP` requires all of:
- E-stop released and stable for configured interval,
- Interlocks healthy,
- Fault root cause acknowledged/cleared,
- Fresh self-test pass,
- Authorized command (local or remote, policy-controlled).

All transitions into and out of `SAFE_STOP` must be logged with reason codes and operator/session identity where available.
