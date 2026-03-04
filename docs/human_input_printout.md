# ColourSorter — Human Input Required (One-Page Printout)

**Purpose:** Finalize open items that require product/engineering decisions or measured data.

| Priority | Area | Human Input Needed | Owner | Due Date | Status |
|---|---|---|---|---|---|
| P1 | README release metadata | Provide real CI badge URL, package badge URL, and official license text/link for `README.md`. |  |  | ☐ |
| P1 | OpenSpec calibration identity | Provide the authoritative `calibration_hash` value (or hash-generation rule) to replace `placeholder_hash` in `docs/openspec/v3/configs/calibration.json`. |  |  | ☐ |
| P1 | ESP32 upgrade plan metrics | Fill each `<insert measured ...>` metric in `docs/esp32_multilane_upgrade_plan.md` with measured baseline/target values (%, ms, MTTR, etc.). |  |  | ☐ |
| P2 | Spreadsheet skill completeness | Decide whether to implement pending formatting/alignment TODOs in `skills/spreadsheets/examples/features/*` or explicitly mark them as intentionally unsupported. |  |  | ☐ |

## Sign-off checklist
- [ ] All placeholders replaced with approved values.
- [ ] Values reviewed by responsible owner(s).
- [ ] Documentation updated and consistent across README/OpenSpec/skills examples.
- [ ] Final QA pass confirms no unresolved TODO/placeholder markers in released docs.
