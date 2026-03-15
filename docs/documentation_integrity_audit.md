# Documentation Integrity Audit

Date: 2026-03-14  
Scope: repository Markdown docs (`*.md`)

## Method
- Checked Markdown links for local-target existence.
- Checked backticked file-path references against repository paths.
- Spot-checked architecture authority statements for consistency.
- Reviewed docs discoverability from top-level README.

## Findings

| Severity | Category | Finding | Evidence | Impact |
|---|---|---|---|---|
| WARNING | References to missing files | `docs/phase3_feature_discovery.md` lists planned API v3 files/tests that do not exist in repo. | `src/coloursorter/api/v3/*.py` and `tests/test_api_v3_*.py` are listed as “New files to add”. | Readers may assume API v3 implementation exists when it does not. |
| WARNING | References to missing files | `docs/pyside6_module_path_regression_rca.md` references schema/spec/test artifacts that are absent. | Mentions `docs/openspec/v3/gui/pyside6_runtime_modules.schema.json`, `pyside6_runtime_modules.yaml`, and `tests/test_pyside6_module_spec_format.py`. | RCA remediation steps are not directly reproducible from current tree. |
| WARNING | Outdated architecture description | Root `openspec.md` declares itself the normative source of truth, while OpenSpec docs define authority under `docs/openspec/`. | Conflicting authority statements between `openspec.md` and `docs/openspec/README.md`. | Misleading governance/contract source selection during audits or implementation. |
| WARNING | Removed/relocated module path terminology | Multiple docs still reference pre-package-root paths (e.g., `deploy/pipeline.py`, `bench/runner.py`) instead of `src/coloursorter/...`. | Present in `TESTING.md` and `DEVELOPER_GUIDE.md`. | Slows onboarding and increases navigation errors for contributors/tools. |
| INFO | Broken links | No broken Markdown links were detected for local link targets. | Automated scan found zero unresolved local Markdown links. | Link hygiene is good. |
| INFO | Orphaned documentation | Many audit/planning docs are not discoverable from `README.md` (no documentation index section). | `README.md` has no centralized docs catalog and only workflow/test sections near the end. | Useful docs are hard to find; increases duplication and drift risk. |
| INFO | Deprecated terminology | `docs/pyside6_runtime_dependency_strategy.md` still uses legacy keys (`schema_version: 1`, `runtime_dependencies`) flagged as drift in RCA. | YAML example and RCA note conflict on expected schema key (`runtime`). | Terminology/schema inconsistency can propagate invalid examples. |

## Command Log (audit checks)
```bash
python - <<'PY'
import re, os, pathlib
root=pathlib.Path('.').resolve()
md_files=[p for p in root.rglob('*.md')]
link_re=re.compile(r'\[[^\]]+\]\(([^)]+)\)')
missing=[]
for f in md_files:
    text=f.read_text(encoding='utf-8',errors='ignore')
    for m in link_re.finditer(text):
        target=m.group(1).strip()
        if not target or target.startswith('#'):
            continue
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://',target) or target.startswith('mailto:'):
            continue
        t=target.split('#')[0].split('?')[0].strip().strip('<>')
        if not t:
            continue
        cand=(f.parent / t).resolve() if not os.path.isabs(t) else (root / t.lstrip('/')).resolve()
        if not cand.exists():
            missing.append((str(f.relative_to(root)),target))
print('missing',len(missing))
PY
```

