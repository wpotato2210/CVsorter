# OpenSpec Gap Audit

## Top-level repository entries
`.git`, `README.md`, `bench`, `configs`, `contracts`, `data`, `docs`, `gui`, `protocol`, `share`, `skills`, `src`, `tests`.

## Notes
- `OPENSPEC.md` was not found in the repository; audit used available OpenSpec docs under `docs/openspec/`.
- Because `P0` and roadmap stage definitions (`Assessment`, `CoreFunctionality`, `Performance`, `Features`, `Testing`, `Release`) are not specified in-repo, missing items are marked as `Unspecified (source spec missing)`.

| Module | ExistingFiles | MissingP0 | MissingRoadmap |
| --- | --- | --- | --- |
| preprocess | `src/coloursorter/preprocess/__init__.py`; `src/coloursorter/preprocess/lane_segmentation.py`; `tests/test_preprocess.py` | Unspecified (source spec missing) | Assessment/CoreFunctionality/Performance/Features/Testing/Release: Unspecified (source spec missing) |
| model | `src/coloursorter/model/__init__.py`; `src/coloursorter/model/types.py` | Unspecified (source spec missing) | Assessment/CoreFunctionality/Performance/Features/Testing/Release: Unspecified (source spec missing) |
| train | `src/coloursorter/train/__init__.py`; `src/coloursorter/train/__main__.py` | Unspecified (source spec missing) | Assessment/CoreFunctionality/Performance/Features/Testing/Release: Unspecified (source spec missing) |
| eval | `src/coloursorter/eval/__init__.py`; `src/coloursorter/eval/rules.py`; `tests/test_eval.py` | Unspecified (source spec missing) | Assessment/CoreFunctionality/Performance/Features/Testing/Release: Unspecified (source spec missing) |
| deploy | `src/coloursorter/deploy/__init__.py`; `src/coloursorter/deploy/pipeline.py`; `src/coloursorter/deploy/webcam.py`; `tests/test_deploy_failure_modes.py` | Unspecified (source spec missing) | Assessment/CoreFunctionality/Performance/Features/Testing/Release: Unspecified (source spec missing) |
