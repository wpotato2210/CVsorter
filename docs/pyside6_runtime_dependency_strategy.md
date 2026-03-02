# PySide6 Runtime Dependency Prevention Strategy

This proposal prevents runtime surprises from PySide6 module split changes (for example, `QState` / `QStateMachine` living in `PySide6.QtStateMachine` in some versions).

## 1) Explicit dependency management

### `pyproject.toml` guidance

Pin direct dependencies and include known runtime helpers explicitly:

```toml
[project]
dependencies = [
  "PySide6>=6.6,<7.0",
  "PySide6-Addons>=6.6,<7.0",
  "PyYAML>=6.0,<7.0",
]
```

Implementation notes:

- Keep `PySide6` and `PySide6-Addons` on the same version window.
- Do not rely on transitive installation of optional Qt submodules.
- Treat GUI runtime validator dependencies (for example `PyYAML`) as explicit first-class dependencies.

## 2) Modular import strategy

### Rule

Import Qt classes from the upstream module where they are defined, not from broad legacy buckets.

### Refactor example

Before:

```python
from PySide6.QtCore import QObject, QState, QStateMachine, QTimer, Signal, Slot
```

After:

```python
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtStateMachine import QState, QStateMachine
```

Rationale:

- Mirrors upstream module layout and reduces ambiguity on upgrades.
- Makes module dependency review and static scanning straightforward.
- Lets validators detect missing optional modules before runtime state machine startup.

## 3) OpenSpec + agents integration

### YAML schema extension

Track runtime Qt module dependencies per GUI component in OpenSpec:

```yaml
schema_version: 1
runtime_dependencies:
  package: PySide6
  min_version: "6.6"
  max_version_exclusive: "7.0"
  required_modules:
    - PySide6.QtCore
components:
  bench_controller_state_machine:
    owners: [gui/bench_app/controller.py]
    required_modules: [PySide6.QtStateMachine, PySide6.QtCore, PySide6.QtWidgets]
```

### `openspec.md` entry pattern

```md
| GUI runtime module dependencies | `docs/openspec/v3/gui/pyside6_runtime_modules.yaml` | `gui/bench_app/*.py` |
```

### Agent validation workflow

- During bench bring-up and CI, run `python tools/validate_pyside6_modules.py`.
- Fail immediately if any module listed in the OpenSpec YAML cannot be imported.
- Require updates to the YAML spec in the same change where GUI imports are changed.

## 4) Version-aware CI / virtualenv automation

Use `tools/validate_pyside6_modules.py` to:

- detect installed PySide6 version,
- import-check required submodules with `importlib`,
- fail fast on missing modules.

### CI integration recommendation

Add a workflow step before GUI/unit tests:

```yaml
- name: Validate PySide6 runtime modules
  run: python tools/validate_pyside6_modules.py
```

For local development, run in a fresh virtual environment after dependency install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
python tools/validate_pyside6_modules.py
```

## 5) Submodule usage documentation table

Keep a single source of truth in YAML (`docs/openspec/v3/gui/pyside6_runtime_modules.yaml`) and optionally mirror it in markdown for review ergonomics:

| GUI component | Owner files | Required submodules |
|---|---|---|
| `bench_controller_state_machine` | `gui/bench_app/controller.py` | `PySide6.QtStateMachine`, `PySide6.QtCore`, `PySide6.QtWidgets` |
| `bench_main_window` | `gui/bench_app/app.py` | `PySide6.QtWidgets`, `PySide6.QtGui`, `PySide6.QtCore` |
| `ui_loader` | `gui/bench_app/load_ui_main_layout.py` | `PySide6.QtUiTools`, `PySide6.QtWidgets`, `PySide6.QtCore` |

Maintenance rule:

- Any PR touching imports in `gui/bench_app` must update the OpenSpec YAML and pass validator checks.
