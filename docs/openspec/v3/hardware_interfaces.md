# OpenSpec v3 Hardware Interfaces Profile

## Scope
This document defines OpenSpec v3 hardware-adjacent contracts for machine vision, lighting, motion feedback, actuation, and industrial communications. It also maps each interface to the currently deployed serial bench protocol so migrations can be staged without breaking existing bring-up and validation flows.

## 1) Camera support contract

### 1.1 Transport and trigger support matrix

| Camera interface | Typical link budget | Trigger types | Expected FPS / operating range | Timestamping expectation |
| --- | --- | --- | --- | --- |
| GigE Vision (1/2.5/5/10GigE) | 1-10 Gbps per camera, with jumbo frames strongly recommended | `free-run`, `hardware-trigger`, `encoder-synced` | 25-300 FPS at line-scan/area-scan production resolutions (exact FPS depends on payload + NIC QoS) | Camera-provided hardware timestamp is required when available; host acquisition timestamp is fallback only and must be marked `timestamp_source=host_fallback`. |
| USB3 Vision | 5-20 Gbps nominal (USB 3.x generation dependent), direct host bus topology preferred | `free-run`, `hardware-trigger`, `encoder-synced` | 30-240 FPS in standard ROI configurations; avoid sustained >80% bus occupancy | Use device monotonic timestamp if exposed by vendor SDK; otherwise host timestamp with measured transfer jitter budget attached to metadata. |
| CameraLink (Base/Medium/Full) | Deterministic frame-grabber path, low-jitter trigger propagation | `free-run`, `hardware-trigger`, `encoder-synced` | 60-800 FPS depending on tap format, bit depth, and frame-grabber capabilities | Frame-grabber clock timestamp is normative. If camera embeds line/frame counter, host must persist both counter and grabber timestamp for alignment audits. |

### 1.2 Trigger semantics
- `free-run`: camera owns cadence; scheduler consumes frame timestamps and current speed estimate.
- `hardware-trigger`: camera exposure starts from deterministic trigger edge.
- `encoder-synced`: capture trigger derived from encoder phase/position; must maintain phase lock in production mode.

### 1.3 Compatibility mapping to current serial bench protocol
The current serial bench protocol does not configure camera transport or trigger mode directly. Camera control remains local to edge acquisition services; serial bench messages only influence sort decision timing and machine mode:

| Hardware interface function | Current serial bench compatibility |
| --- | --- |
| Select camera transport (GigE/USB3/CameraLink) | Not represented on wire (`N/A` in `<CMD|...>` command set). |
| Select trigger type (`free-run`, `hardware-trigger`, `encoder-synced`) | Not represented on wire (`N/A` in `<CMD|...>` command set). |
| Consume timestamped detections for reject scheduling | Indirectly compatible via `SCHED` trigger distance argument once detections are converted to trigger positions. |

## 2) Lighting control contract

### 2.1 PWM dimming API
Normative software contract:
- `set_intensity(channel_id, duty_cycle_pct, slew_ms=0)` where `duty_cycle_pct` in `[0.0, 100.0]`.
- `get_intensity(channel_id) -> duty_cycle_pct`.
- `set_profile(profile_id, channel_map)` for recipe-level presets.

Behavioral constraints:
- PWM carrier frequency must avoid camera exposure alias bands (recommended >= 20 kHz for most global shutter deployments).
- Intensity command-to-output settling should be bounded and published by hardware profile (`t_settle_us`).

### 2.2 Strobe sync timing
- `arm_strobe(channel_id, lead_us, pulse_us, source)` where `source` can be `camera_trigger`, `encoder_phase`, or `software`.
- Deterministic timing target: edge-to-light-on jitter <= 10 us for hardware-routed trigger paths.
- Strobe metadata must include `armed_at`, `fired_at`, and `source` to support frame-level illumination audits.

### 2.3 Ambient compensation inputs
- Contracted inputs: `ambient_lux`, `sensor_temp_c`, optional `line_voltage_v`.
- Compensation function may be static LUT or adaptive controller but must expose effective output as `compensated_duty_cycle_pct`.

### 2.4 Compatibility mapping to current serial bench protocol
- No dedicated lighting command exists in the current serial command surface (`SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`).
- Lighting control is therefore out-of-band for bench serial and should be integrated through local service APIs, with results reflected only in downstream detection quality and scheduling outcomes.

## 3) Motion / encoder interface

### 3.1 Quadrature input assumptions
- Incremental encoder with A/B channels, optional Z index.
- Electrical expectation: differential or noise-hardened single-ended input with debounce/filter tuned to max line speed.
- Decode mode must be declared (`x1`, `x2`, `x4`) because all distance and speed derivations depend on effective counts-per-revolution.

### 3.2 Speed estimation formula
For sample window `[t0, t1]`:

`belt_speed_mm_s = ((count_1 - count_0) / counts_per_mm) / (t1 - t0)`

Where:
- `count_0`, `count_1` are unwrapped quadrature counts.
- `counts_per_mm` is calibration-derived and lane-geometry-consistent.
- `(t1 - t0)` is in seconds.

Recommended implementation detail: combine finite-difference estimate with low-latency filtering (e.g., EMA) and expose both `belt_speed_raw_mm_s` and `belt_speed_mm_s`.

### 3.3 Phase alignment API and tolerance
Normative API surface:
- `set_phase_offset_deg(offset_deg)`
- `get_phase_error_deg() -> float`
- `sync_to_index(timeout_ms)`

Tolerance targets:
- Steady-state phase error: `|phase_error_deg| <= 2.0` during production.
- Encoder-synced capture/eject path should maintain cumulative distance error <= 1.0 mm over a single reject flight window.

### 3.4 Compatibility mapping to current serial bench protocol
- Encoder counts, phase error, and speed are not directly exchanged over `<CMD|arg1|arg2>` today.
- Compatibility point: host-side scheduler converts motion model outputs into `SCHED(lane, trigger_mm)` commands; this keeps existing serial firmware interfaces stable while motion IO evolves.

## 4) Actuator interface

### 4.1 Eject pulse timing schema
Normative schema fields (per fire event):
- `lane_index`
- `fire_at_mm` or `fire_at_tick`
- `pulse_width_ms`
- `driver_channel`
- `request_id` / `trace_id`

### 4.2 Pulse width bounds
- Solenoid default operating envelope: `4.0 ms <= pulse_width_ms <= 40.0 ms`.
- Pneumatic valve default operating envelope: `10.0 ms <= pulse_width_ms <= 120.0 ms`.
- Per-lane overrides allowed but must stay within hardware safety limits and be recipe-auditable.

### 4.3 Confirmation sensor feedback handling
- Expected feedback inputs: coil current sense, reed/prox confirmation, or pressure switch confirmation.
- Feedback states: `FIRED_CONFIRMED`, `FIRED_UNCONFIRMED`, `MISFIRE`, `LATE_FIRE`.
- If confirmation fails, system should:
  1. record fault telemetry with lane + request id,
  2. increment actuator health counters,
  3. optionally degrade lane or transition to maintenance-safe policy based on configured thresholds.

### 4.4 Compatibility mapping to current serial bench protocol
- Current serial protocol schedules ejection intent via `SCHED` but does not expose explicit pulse-width or actuator feedback commands.
- Existing compatibility model: actuator pulse generation + confirmation handling occur behind MCU/IO abstraction, while bench serial remains command-minimal.

## 5) Industrial communications profile

### 5.1 Control-plane protocols
Primary interoperability targets:
- EtherCAT
- Profinet
- EtherNet/IP

Normative expectation: each profile must support mode control, run/stop intent, fault summary, and heartbeat/watchdog exchange compatible with OpenSpec mode semantics.

### 5.2 Legacy Modbus TCP mapping
When legacy PLC integration is required, provide a fixed register map for minimum viable interoperability:
- Holding registers: mode command, queue depth mirror, last fault code.
- Input registers: current mode, scheduler state, belt speed (scaled), system heartbeat counter.
- Coils/discretes: run-enable, reset-fault, e-stop status mirror.

### 5.3 Telemetry transport profile (MQTT / AMQP)
Recommended topic/routing structure:
- `openspec/v3/telemetry/machine/{machine_id}/cycle`
- `openspec/v3/telemetry/machine/{machine_id}/fault`
- `openspec/v3/telemetry/machine/{machine_id}/actuator/{lane}`
- `openspec/v3/state/machine/{machine_id}/summary`

Message expectations:
- At-least-once delivery for fault/state topics.
- Ordered partitioning per machine for cycle telemetry where supported.
- Include `trace_id`/`request_id` correlation fields for cross-layer debugging.

### 5.4 Compatibility mapping to current serial bench protocol
- Serial bench protocol remains the local host↔MCU control path and is complementary to plant/SCADA communications.
- `SET_MODE` maps to external run mode intents.
- `GET_STATE`/ACK snapshots map to PLC-readable state mirrors.
- `SCHED` and `RESET_QUEUE` remain internal control-plane operations and are typically not forwarded to plant buses directly.

## 6) Consolidated compatibility summary (serial bench protocol)

| New hardware interface area | Direct support in current serial bench protocol | Bridge strategy |
| --- | --- | --- |
| Camera transport + triggering | No | Keep in acquisition service; emit normalized detections to scheduler. |
| Lighting dimming + strobe + ambient compensation | No | Manage out-of-band in lighting controller service; record telemetry for audits. |
| Encoder phase/speed telemetry and APIs | Partial (indirect) | Convert to `SCHED` trigger distance and scheduler timing inputs. |
| Actuator pulse profile + confirmation feedback | Partial (indirect) | Keep inside MCU/IO layer; surface aggregate state via `GET_STATE` and telemetry. |
| EtherCAT/Profinet/EtherNet-IP/Modbus/MQTT/AMQP integration | No (not on serial wire) | Implement at gateway/edge integration layer with mode/state mapping to serial command model. |
