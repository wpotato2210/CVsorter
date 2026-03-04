# OpenSpec v3 Governance

## Scope

This document defines project governance for OpenSpec v3 artifacts, including licensing, contribution workflow, release cadence, and support windows.

## License recommendation

OpenSpec v3 specifications and reference implementation code should use **Apache License 2.0**.

Recommended policy:
- Spec documents (`docs/openspec/**`) are published under Apache-2.0.
- Reference code and test harnesses that implement OpenSpec behavior are published under Apache-2.0.
- Third-party dependencies retain their own licenses and must be tracked in repository notices.

Rationale:
- Permissive adoption for vendors and integrators.
- Explicit patent grant to reduce downstream IP risk.
- Clear contribution and redistribution conditions for ecosystem growth.

## Contribution workflow

### Pull request template requirements

Every PR touching OpenSpec artifacts must include:
- Summary of spec or behavior changes.
- Backward compatibility impact (`none`, `additive`, `breaking`).
- Validation evidence (tests, benchmark output, or conformance report).
- Migration guidance when behavior changes are additive or breaking.

### Required checks before merge

Minimum required checks:
1. Unit/integration tests relevant to changed modules.
2. OpenSpec conformance checks (schema/protocol/state/timing where applicable).
3. Documentation parity check for any normative spec changes.
4. CI quality gates defined in `docs/openspec/v3/validation_plan.md` for performance-sensitive changes.

Approval and review policy:
- Minimum **1 maintainer approval** for docs-only changes.
- Minimum **2 approvals** (including at least one code owner) for protocol, timing, or state-machine changes.
- Breaking changes require explicit release-note entry in the PR.

## Release cadence

OpenSpec v3 follows a predictable release train:
- **Minor release cadence:** every 8 weeks.
- **Patch release cadence:** as needed, typically within 2 weeks for critical defects.
- **Release candidates (RC):** cut 7 days before minor release; only stabilization fixes allowed.

Versioning policy (SemVer):
- MAJOR: backward-incompatible specification or protocol changes.
- MINOR: backward-compatible feature additions or clarified normative rules.
- PATCH: backward-compatible fixes, editorial corrections, non-breaking compliance updates.

## LTS and support windows

Support policy:
- The latest minor release is designated **Current Stable**.
- Every second minor release is designated **LTS**.

Support windows:
- **Current Stable:** full support until next minor release + 30 days.
- **LTS:** 12 months of security and critical bug fixes from LTS release date.
- **End-of-support:** after window closure, fixes are best-effort and may require upgrade.

Backport policy:
- Security fixes: backport to all supported LTS versions.
- Critical correctness fixes: backport to Current Stable and latest LTS.
- Feature changes are not backported unless required for compliance parity.

## Governance updates

Changes to this governance policy require:
1. PR with rationale and impact summary.
2. Review by at least two maintainers.
3. Effective date and migration notes when policy requirements change.
