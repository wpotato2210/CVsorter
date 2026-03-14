# CI Failure RCA: firmware readiness strict gate import drift

## Failure summary
- Failing test: `tests/test_firmware_readiness_check.py::test_firmware_readiness_check_script_passes`
- Failure type: `AssertionError` due to non-zero subprocess exit code from `python tools/firmware_readiness_check.py --strict`

## Root error
- Origin module: `src/coloursorter/config/runtime.py`
- Origin line: `_validate_detection_provider_name` imports `resolve_detection_provider_name` from `coloursorter.deploy`
- Failing path: `tools/firmware_readiness_check.py::check_runtime_config` injected a stub `coloursorter.deploy` containing `DETECTION_PROVIDER_VALUES` but not `resolve_detection_provider_name`, causing an import/attribute failure during runtime config validation

## CI-specific impact
- Workflow runs strict readiness in both jobs:
  - packaging: `python tools/firmware_readiness_check.py --strict`
  - tests (indirectly via pytest subprocess test)
- A failure here fails the CI workflow despite all other tests passing.

## Minimal fix
- Ensure the readiness-check stub defines both:
  - `DETECTION_PROVIDER_VALUES`
  - `resolve_detection_provider_name(name: str) -> str`
- Keep deterministic behavior by validating against fixed allowed provider values.
