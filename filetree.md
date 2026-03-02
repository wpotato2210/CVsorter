# filetree.md

## Scope
Reverse-engineered repository layout for ChatGPT task routing.

## Dependencies
- Project metadata: `pyproject.toml`, `README.md`
- Architecture/spec context: `architecture.md`, `openspec.md`, `docs/openspec/**`

## Curated file tree
```text
ColourSorter/
├── src/coloursorter/
│   ├── bench/                # bench runner, sources, transport, evaluation, CLI
│   ├── calibration/          # px↔mm mapping
│   ├── config/               # runtime config schema/load/validation
│   ├── deploy/               # end-to-end decision pipeline orchestration
│   ├── eval/                 # rule evaluation / rejection decisions
│   ├── model/                # typed contracts (frame/detection/decision)
│   ├── preprocess/           # lane segmentation / geometric preprocessing
│   ├── protocol/             # protocol constants, host model, mode policy, NACK mapping
│   ├── scheduler/            # schedule command generation
│   ├── serial_interface/     # wire framing, packet parse/serialize
│   └── train/                # artifact/training placeholders
├── gui/bench_app/            # Qt bench app (window/controller/.ui loader)
├── contracts/                # JSON schemas (frame/schedule/mcu_response)
├── protocol/                 # command contract JSON
├── configs/                  # default runtime/bench/calibration/lane configs
├── data/                     # manifest artifacts
├── docs/
│   ├── openspec/v3/          # OpenSpec mirrors + governance docs
│   └── artifacts/            # readiness and trace outputs
├── tests/                    # unit/integration/protocol/compliance coverage
├── tools/                    # operational/report scripts
└── skills/                   # local skill assets
```

## Task → primary files
| Task | Primary files |
| --- | --- |
| Protocol changes | `src/coloursorter/protocol/*`, `protocol/commands.json`, `tests/test_protocol_compliance_v3.py` |
| Wire framing/parsing | `src/coloursorter/serial_interface/serial_interface.py`, `src/coloursorter/serial_interface/wire.py`, `tests/test_serial_interface.py` |
| Scheduling | `src/coloursorter/scheduler/output.py`, `tests/test_scheduler.py` |
| Bench runtime | `src/coloursorter/bench/*`, `tests/test_bench_*` |
| GUI control flow | `gui/bench_app/controller.py`, `gui/bench_app/app.py`, `tests/test_bench_controller_gui.py` |
| OpenSpec parity | `docs/openspec/v3/**`, `tests/test_openspec_artifacts.py` |
