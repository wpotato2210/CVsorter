# OpenSpec Documentation Index

This directory consolidates OpenSpec v3 artifacts that were previously stored across `contracts/`, `protocol/`, `data/`, `configs/`, and `gui/`.

## Branch verification and diff status

- Target remote branch: `OpenSpec-import`.
- Verification command used: `git ls-remote --heads origin OpenSpec-import`.
- Result: no `origin` remote is configured in this repository, so remote verification and branch fetch could not be completed in this environment.
- Fallback used for this import pass: import all OpenSpec-like artifacts currently present on `work` into `docs/openspec/v3/` with commit provenance.

## v3 spec-to-implementation mapping

| Spec artifact | Implementation modules | Notes |
| --- | --- | --- |
| `v3/protocol/commands.json` | `tests/test_serial_interface.py`, `tests/test_integration.py` | Command shapes and protocol expectations consumed by serial/integration tests. |
| `v3/contracts/frame_schema.json` | `tests/test_preprocess.py`, `tests/test_integration.py` | Frame payload schema constraints for preprocessing and end-to-end checks. |
| `v3/contracts/mcu_response_schema.json` | `tests/test_serial_interface.py`, `tests/test_integration.py` | MCU response validation targets serial and integration coverage. |
| `v3/contracts/sched_schema.json` | `tests/test_scheduler.py`, `tests/test_integration.py` | Scheduler message/state schema aligns with scheduler and integration tests. |
| `v3/data/manifest.json` | `src/coloursorter/ingest/adapter.py`, `tests/test_integration.py` | Top-level artifact index and ingest-facing artifact mapping context. |
| `v3/configs/default_config.yaml` | `src/coloursorter/config/runtime.py`, `tests/test_openspec_artifacts.py` | Canonical runtime config keys for MCU selector + serial defaults and parity coverage. |
| `v3/configs/calibration.json` | `tests/test_camera.py`, `tests/test_integration.py` | Camera calibration parameters used in camera/integration validation. |
| `v3/configs/lane_geometry.yaml` | `tests/test_preprocess.py`, `tests/test_integration.py` | Lane geometry assumptions used by preprocessing and integration checks. |
| `v3/gui/ui_main_layout.json` | `gui/bench_app/load_ui_main_layout.py`, `tests/test_openspec_artifacts.py` | GUI contract includes selectors/controls for MCU + serial + manual servo + logging, with parity guards. |

## Provenance (for v4 migration traceability)

Source commit for all files imported in this pass: `01cf4bd17fb56664efe11f0ca67d427f62469c66`.

| Imported file | Source file on `work` | Source commit |
| --- | --- | --- |
| `docs/openspec/v3/protocol/commands.json` | `protocol/commands.json` | `01cf4bd17fb56664efe11f0ca67d427f62469c66` |
| `docs/openspec/v3/contracts/frame_schema.json` | `contracts/frame_schema.json` | `01cf4bd17fb56664efe11f0ca67d427f62469c66` |
| `docs/openspec/v3/contracts/mcu_response_schema.json` | `contracts/mcu_response_schema.json` | `01cf4bd17fb56664efe11f0ca67d427f62469c66` |
| `docs/openspec/v3/contracts/sched_schema.json` | `contracts/sched_schema.json` | `01cf4bd17fb56664efe11f0ca67d427f62469c66` |
| `docs/openspec/v3/data/manifest.json` | `data/manifest.json` | `01cf4bd17fb56664efe11f0ca67d427f62469c66` |
| `docs/openspec/v3/configs/default_config.yaml` | `configs/default_config.yaml` | `01cf4bd17fb56664efe11f0ca67d427f62469c66` |
| `docs/openspec/v3/configs/calibration.json` | `configs/calibration.json` | `01cf4bd17fb56664efe11f0ca67d427f62469c66` |
| `docs/openspec/v3/configs/lane_geometry.yaml` | `configs/lane_geometry.yaml` | `01cf4bd17fb56664efe11f0ca67d427f62469c66` |
| `docs/openspec/v3/gui/ui_main_layout.json` | `gui/ui_main_layout.json` | `01cf4bd17fb56664efe11f0ca67d427f62469c66` |



## Architecture document authority

- Process references to `architecture/*` are legacy wording from pre-import layouts.
- The canonical architecture authority for OpenSpec is `docs/openspec/v3/system_architecture.md`.
- State-machine command/fault behavior remains normative in `docs/openspec/v3/state_machine.md` and `docs/openspec/v3/firmware_state_machine.md`.

## Governance artifacts

- System architecture and operating modes: `docs/openspec/v3/system_architecture.md`.
- Hardware interfaces profile and serial bench compatibility mapping: `docs/openspec/v3/hardware_interfaces.md`.
- Interface Control Document: `docs/openspec/icd.md`.
- Protocol matrix: `docs/openspec/v3/protocol_compliance_matrix.md`.
- System matrix (state/timing/telemetry): `docs/openspec/v3/system_compliance_matrix.md`.
- Validation plan and CI quality gates: `docs/openspec/v3/validation_plan.md`.
- Governance policy (license, contributions, release/support): `docs/openspec/v3/governance.md`.
