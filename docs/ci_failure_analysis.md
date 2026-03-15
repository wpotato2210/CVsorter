# CI Failure Analysis

## Observed failing command
`PYTHONPATH=src python -m pytest tests -q --cov=src/coloursorter --cov-report=xml`

## Failure
Pytest exits with:

```
error: unrecognized arguments: --cov=src/coloursorter --cov-report=xml
```

This indicates `pytest-cov` is unavailable in the active environment, so pytest cannot parse `--cov` flags.

## Likely root cause
Missing `pytest-cov` in the runtime environment used to execute the workflow test command.

## Minimal fix
Ensure the CI job installs test extras with safe quoting and then verify plugin presence before running pytest:

```bash
python -m pip install -e ".[test]"
python -m pytest --help | grep -- --cov
```

Or add explicit install fallback:

```bash
python -m pip install -e ".[test]" pytest-cov
```
