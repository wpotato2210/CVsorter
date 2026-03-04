# Surgical Technical Audit — ColourSorter

## 1) Project Intent (≤80 words)
This repository is not a résumé/CV parser. It is a deterministic bench/runtime stack for lane-based vision sorting with scheduler + MCU transport validation. Real users are controls/firmware/vision engineers validating machine timing, queue safety, and protocol behavior, plus operators using the bench GUI. NOT EVIDENT IN REPO: recruiter-facing document ingestion, candidate ranking workflows, or ATS integrations.

## 2) OpenSpec Deep Audit
### Findings
- OpenSpec is mixed: partly contractual (mirrored JSON schemas/config artifacts) and partly descriptive (broad state/timing prose).
- Inputs/outputs are formally defined for protocol/contracts artifacts, but not for all narrative sections.
- Determinism is explicitly targeted, but timing values in core spec remain placeholders.
- Versioning exists (`v3` path), but governance is weak: no machine-enforced semantic version process for breaking/non-breaking changes.
- Drift is already acknowledged in code: ingest validation bypasses parts of shared contract due incompatibility.

### Spec maturity score
**5/10**

### Top 5 production-breaking gaps
1. Timing budgets in OpenSpec are still placeholders (`<insert ...>`), so safety margins are unprovable.
2. OpenSpec suitability claim is conditional (“if validated”), not an acceptance gate tied to measurable CI/hardware criteria.
3. Contract compatibility is not strict end-to-end: ingest adapter intentionally filters contract requirements to stay operable.
4. Spec contains large behavioral surface (state machine, safety, edge cases) but no executable conformance harness enforcing all of it.
5. Version directory (`v3`) exists, but no formal migration policy in artifact files for consumers (deprecation window, compatibility contract, rollback semantics).

## 3) Architecture Forensics
### Assessment
- Module boundaries are mostly layered (ingest/preprocess/deploy/scheduler/serial/bench), but orchestration classes absorb policy and glue logic heavily.
- Separation of concerns is moderate: pipeline logic is clear, yet runtime/bench classes mix timing, fallback policy, transport semantics, and telemetry packing.
- Dependency direction is mostly inward to domain modules, but hidden coupling exists via shared runtime files and mirrored specs.
- State management correctness is decent for deterministic loops, but mutable in-memory caches + file-mtime reloads create runtime sensitivity to filesystem events.
- Error handling is explicit with custom exceptions at boundaries; fallback behavior can silently degrade outputs (e.g., zeroed centroid/trigger paths).
- Observability is bench-centric; no metrics backend/export path found.
- Config management is over-centralized in one parser/model path.
- Testability is strong in bench/protocol areas, weaker for true hardware/runtime uncertainty.

### Flags
- **God file**: runtime config loader/parser is excessively centralized.
- **Shotgun parsing**: custom YAML parser + many manual field validators.
- **Hard-coded assumptions**: fixed lane expectations, frame shape assumptions, static command framing.
- **Accidental complexity**: bench runner handles policy, transport, telemetry, and safety checks in one execution surface.

### Architecture score
**6/10**

### Single most dangerous design flaw
**Spec/contract integrity is not authoritative at runtime** (adapter-side compatibility bypass), which allows silent divergence between declared contracts and executed behavior.

## 4) Parsing & Data Pipeline Risk (CV tools)
### Reality check
This repository does not implement résumé/CV document parsing. It ingests camera frames + synthetic/object detections for physical sorter decisions.

- CV ingestion: replay/live camera frames (file/video/camera).
- Text extraction: **NOT EVIDENT IN REPO**.
- Structure inference for résumés: **NOT EVIDENT IN REPO**.
- Candidate ranking/scoring: **NOT EVIDENT IN REPO**.

### Stress test against résumé parser scenarios
- multi-column PDFs: **NOT EVIDENT IN REPO**
- tables: **NOT EVIDENT IN REPO**
- academic CVs: **NOT EVIDENT IN REPO**
- missing sections: **NOT EVIDENT IN REPO**
- non-English text: **NOT EVIDENT IN REPO**
- malformed files: only image/video/camera handling exists; non-image replay sources raise errors.

### Robustness score (for résumé/CV parsing use-case)
**0/10**

### Top 5 real-world failure modes (if deployed as recruiter CV tool)
1. Cannot ingest PDF/DOCX at all.
2. No OCR/text extraction path.
3. No semantic section detection (experience/education/skills).
4. No ranking logic for candidates.
5. No multilingual normalization or document schema reconciliation.

### Grade
**Demo-grade for bean/colour sorting bench. Not production-grade for recruiter CV processing.**

## 5) Implementation Maturity
### Component classification
- **Production-ready (relative to bench scope):** protocol framing/parsing, scheduler bounds checks, contract parity tests.
- **Partially implemented:** live runtime loop and detection providers (simple CV heuristics + transport integration).
- **Stubbed/scaffold:** model training path (`baseline-model-stub`, stub predictor).
- **Missing but implied:** production observability stack (metrics backend), strict spec conformance gate, operational config rollout governance.

### Overall stage
**Serious prototype (approaching pre-production for bench validation only).**

## 6) Performance & Scale Reality Check
### Evidence
- No batching pipeline for inference decisions.
- No streaming backpressure beyond bounded ingest capacity and drop policy.
- Limited memory discipline patterns (iterative frame processing; no explicit large-file strategies).
- Mostly synchronous loop; no async/concurrency model for high-throughput scaling.
- Large-file replay support exists for videos but without explicit resource governance for long-duration runs.

### Scale readiness score
**4/10**

## 7) Test Suite Autopsy
### Assessment
- Coverage breadth is good across protocol, scheduler, ingest, config, determinism telemetry, and integration.
- Strong parity checks for OpenSpec artifact mirroring.
- Many deterministic/hardening checks; little evidence of property-based fuzzing.
- Fixtures are mostly synthetic; real-world camera/domain variability risk remains.
- Regression protection is strong for known protocol semantics.

### Test maturity score
**7/10**

### Most dangerous missing test
A long-duration, adversarial soak test combining live camera jitter + serial transport faults + config hot-reload races to verify no silent safety drift under sustained load.

## 8) Security & Safety Risks
Concrete findings:
1. Untrusted image/video parsing is delegated to OpenCV without documented sandboxing/isolation strategy.
2. Runtime accepts filesystem paths for configs and sources; no explicit path allowlisting policy evident.
3. Contract mismatch tolerance in ingest adapter can hide malformed producer behavior behind partial validation.
4. No secrets leakage obvious in repository scan (no concrete secret material found).
5. LLM prompt-injection surface: **NOT EVIDENT IN REPO**.

## 9) Top 10 High-Leverage Fixes (prioritized)
1. **Make OpenSpec timing values executable and mandatory** — Impact: High, Effort: M.
   - Why: Removes unverifiable safety claims.
   - Change: Replace placeholders with measured limits; enforce in CI + hardware gate script.

2. **Eliminate ingest contract bypass** — Impact: High, Effort: M.
   - Why: Prevents silent spec drift.
   - Change: Split schemas by boundary purpose or version contract; fail hard on mismatch.

3. **Decompose runtime config parser** — Impact: High, Effort: M.
   - Why: Current monolith is a maintenance and defect hotspot.
   - Change: Move domain-specific parsing into independent modules + typed schema validation.

4. **Refactor bench runner into pipeline stages** — Impact: High, Effort: L.
   - Why: Reduces accidental complexity and enables isolated testing.
   - Change: Separate ingest validation, decision policy, transport dispatch, telemetry emission.

5. **Introduce property-based fuzz tests for protocol/ingest parsing** — Impact: High, Effort: M.
   - Why: Current tests are broad but mostly example-driven.
   - Change: Add hypothesis-based malformed-frame/payload generators.

6. **Add hardened media input policy** — Impact: Med, Effort: M.
   - Why: Untrusted parser exposure.
   - Change: Pre-validate mime/container, size caps, decode budget timeouts, sandbox strategy.

7. **Add metrics export (Prometheus/OpenTelemetry)** — Impact: Med, Effort: M.
   - Why: Logs alone are insufficient for production diagnosis.
   - Change: Export latency, queue age, nack codes, watchdog transitions.

8. **Formalize OpenSpec version contract** — Impact: Med, Effort: S.
   - Why: Prevents compatibility ambiguity.
   - Change: Semver for schemas/protocol; change log with migration policy and deprecation windows.

9. **Run continuous stress/soak benchmarks in CI nightly** — Impact: Med, Effort: M.
   - Why: Safety regressions often time-dependent.
   - Change: Add deterministic replay stress matrix + artifact trend alarms.

10. **Clarify product scope in top-level docs** — Impact: Med, Effort: S.
   - Why: Prevents category mismatch (CV résumé parser vs computer vision sorter).
   - Change: Explicit non-goals and target users in README + docs.

## 10) Final Brutal Verdict (≤120 words)
Would this survive real recruiter workloads today? **No.** It is not that product. This repo is a bench/runtime stack for physical vision sorting, not document parsing, extraction, or candidate ranking. For its actual domain, it shows disciplined deterministic testing and protocol rigor, but still has dangerous maturity gaps: incomplete OpenSpec timing contract, contract/implementation drift tolerance, monolithic config parsing, and limited production observability. Before serious trust: make spec executable, remove contract bypasses, split orchestration hotspots, and prove long-duration fault tolerance under realistic hardware jitter and transport failure patterns.
