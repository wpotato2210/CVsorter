# OpenSpec Documentation Index

This directory consolidates OpenSpec v3 artifacts that were previously stored across `contracts/`, `protocol/`, `data/`, `configs/`, and `gui/`.

## Branch verification and diff status

- Canonical branch target for import history: `OpenSpec-import`.
- Verification command: `git ls-remote --heads <remote> OpenSpec-import`.
- If no remote is configured, treat this directory as source-of-truth and preserve provenance in the table below.

## v3 spec-to-implementation mapping

| Spec artifact | Implementation modules | Notes |
| --- | --- | --- |
| `v3/protocol/commands.json` | `tests/test_serial_interface.py`, `tests/test_integration.py` | Command shapes and protocol expectations consumed by serial/integration tests. |
| `v3/contracts/frame_schema.json` | `tests/test_preprocess.py`, `tests/test_integration.py` | Frame payload schema constraints for preprocessing and end-to-end checks. |
| `v3/contracts/mcu_response_schema.json` | `tests/test_serial_interface.py`, `tests/test_integration.py` | MCU response validation targets serial and integration coverage. |
| `v3/contracts/sched_schema.json` | `tests/test_scheduler.py`, `tests/test_integration.py` | Scheduler message/state schema aligns with scheduler and integration tests. |
| `v3/data/manifest.json` | `tests/test_integration.py`, `README.md` | Top-level artifact index consumed during integration and documentation context. |
| `v3/configs/default_config.yaml` | `src/constants.py`, `tests/test_integration.py` | Runtime defaults and integration test baselines. |
| `v3/configs/calibration.json` | `tests/test_camera.py`, `tests/test_integration.py` | Camera calibration parameters used in camera/integration validation. |
| `v3/configs/lane_geometry.yaml` | `tests/test_preprocess.py`, `tests/test_integration.py` | Lane geometry assumptions used by preprocessing and integration checks. |
| `v3/gui/ui_main_layout.json` | `tests/test_integration.py`, `README.md` | GUI layout contract referenced in integration expectations and project docs. |

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


## Governance artifacts

- Interface Control Document: `docs/openspec/icd.md`.
- Protocol matrix: `docs/openspec/v3/protocol_compliance_matrix.md`.
- System matrix (state/timing/telemetry): `docs/openspec/v3/system_compliance_matrix.md`.

## Recommended maintenance flow

1. Update artifacts under `docs/openspec/v3/`.
2. Refresh matrix files when behavior or contracts change.
3. Run protocol and artifact checks:
   - `pytest -q tests/test_protocol_compliance_v3.py`
   - `pytest -q tests/test_openspec_artifacts.py`
4. Record provenance updates in this file.
