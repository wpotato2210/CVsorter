# PySide6 Module Path Regression RCA

## Scope reviewed
- `tools/validate_pyside6_modules.py`
- `docs/openspec/v3/gui/pyside6_runtime_modules.yaml`
- `docs/openspec/v3/` and OpenSpec index docs
- `pyproject.toml`
- `.github/workflows/ci.yml`, `.github/workflows/hardware-readiness-gate.yml`
- Git history touching validator/spec/workflows

## Key findings

### 1) No single schema-enforced source of truth (high probability)
- Runtime module paths are free-form YAML strings in `docs/openspec/v3/gui/pyside6_runtime_modules.yaml`.
- There is no JSON Schema/YAML schema check in CI for this file; syntax protection is only inside `tools/validate_pyside6_modules.py` runtime logic.
- Existing OpenSpec artifact tests do not assert module-path formatting for this YAML.

### 2) Contributor-facing docs are inconsistent and can seed drift (high probability)
- `docs/pyside6_runtime_dependency_strategy.md` still shows legacy schema keys (`schema_version: 1`, `runtime_dependencies`) while runtime validator now expects `runtime`.
- Repository-wide docs repeatedly use filesystem slash semantics for artifact mirrors (e.g., `contracts/`, `gui/`), creating copy/paste bias toward slash separators.
- One doc uses `PySide6/Qt` phrasing, which is not a valid import path format.

### 3) Validation occurs in CI, but only after commit/push and only if workflow is run (medium-high probability)
- Validation is present in both workflows, but there is no local pre-commit/pre-push guard.
- If branch protection does not require these checks, invalid strings can still be merged.
- Feedback loop is late (remote CI), so regressions are repeatedly reintroduced then fixed.

### 4) YAML parser fallback is intentionally permissive (medium probability)
- If `PyYAML` import fails, validator uses `_simple_yaml_runtime_parse` that extracts only list entries under `runtime.required_modules`/`optional_modules`.
- This parser is robust for lists but does not provide full-structure/schema diagnostics, making malformed specs easier to miss during ad-hoc local runs.

### 5) AI/automation regeneration risk from stale docs and mirror language (medium probability)
- Multiple generated/audit docs indicate AI-assisted document synthesis and path-mirror workflows.
- In that context, slash-based file path conventions are ubiquitous and can leak into module-path fields during regeneration or assisted edits.

## Persistence mechanism (why it keeps coming back)
1. Contributors/automation edit YAML or docs using filesystem mental model (`/`) from surrounding OpenSpec mirror docs.
2. Invalid module strings are not blocked at authoring time (no schema lint, no git hook).
3. Regression is detected only in CI validator step after push (or not detected if check is not required/run).
4. Fix is applied as symptom correction in YAML, but root workflow gaps remain.
5. Next doc- or AI-assisted update repeats step 1.

## Ranked root-cause hypotheses
| Rank | Hypothesis | Probability | Evidence |
|---|---|---:|---|
| 1 | Missing author-time guardrails (schema + hooks) allow bad strings in YAML | High | No pre-commit/pre-push checks; only CI runtime validator |
| 2 | Documentation drift and mixed conventions (path vs module syntax) mislead contributors/tools | High | Legacy schema example + slash-heavy mirror docs |
| 3 | CI enforcement timing/branch policy gap allows invalid merges | Medium-High | Validation is in workflows, but enforcement depends on repo settings |
| 4 | AI-assisted/spec regeneration copies slash path idioms into module fields | Medium | Presence of generated analysis docs + mirror-language patterns |
| 5 | Validator fallback parser hides structural issues in minimal local environments | Medium | Fallback parser performs partial extraction only |

## Architectural fixes (prevent regression)
1. **Add schema-level contract for `pyside6_runtime_modules.yaml`**
   - Introduce `docs/openspec/v3/gui/pyside6_runtime_modules.schema.json`.
   - Enforce regex on each module entry (e.g., `^PySide6\.[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$`).
   - Validate schema in CI and tests.

2. **Shift validation left (local and CI)**
   - Add `pre-commit` hook running `python tools/validate_pyside6_modules.py --spec ...`.
   - Add Make/Nox task (`make validate-spec`) used by contributors and CI.

3. **Make CI gating explicit and early**
   - Ensure runtime-module validation is first required check in protected branch rules.
   - Fail fast before full test matrix to reduce feedback delay.

4. **Remove stale/ambiguous documentation patterns**
   - Update `docs/pyside6_runtime_dependency_strategy.md` to current schema (`runtime`, `schema_version: 3`).
   - Add an explicit “never use `/` in module imports” rule in docs and YAML comments.

5. **Detect drift automatically**
   - Add unit test that loads YAML and asserts every module string passes validator regex.
   - Optional: add script that scans changed lines in PR for `PySide6/` and fails with actionable message.

## Recommended guardrail automation
- `tests/test_pyside6_module_spec_format.py`:
  - parse YAML;
  - validate keys and module format;
  - assert no `/` or `\\` in module strings.
- CI job `lint-openspec` (required):
  - schema validation;
  - `tools/validate_pyside6_modules.py --spec ...`;
  - targeted grep guard for `PySide6/` in OpenSpec YAML/docs examples.
- Contributor workflow:
  - documented one-command local gate (`make validate-spec`) prior to push.
