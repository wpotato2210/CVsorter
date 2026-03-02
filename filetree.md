# filetree.md

## Scope
Reverse-engineered repository map for onboarding and ChatGPT task scoping.

## Top-level tree (curated)
```text
ColourSorter/
├── src/coloursorter/
│   ├── bench/                # Bench runner, frame sources, transport adapters, CLI
│   ├── calibration/          # Pixel-to-mm mapping
│   ├── config/               # Runtime config parsing/validation
│   ├── deploy/               # Pipeline orchestration
│   ├── eval/                 # Decision/reject rules
│   ├── model/                # Core typed contracts
│   ├── preprocess/           # Lane segmentation
│   ├── protocol/             # Protocol constants/host/policy/NACK mapping
│   ├── scheduler/            # Scheduled command output
│   ├── serial_interface/     # Wire encode/decode and packet parsing
│   └── train/                # Artifact/training placeholders
├── gui/bench_app/            # Qt bench GUI controller + window app
├── tests/                    # Unit/integration/compliance tests
├── contracts/                # JSON schemas (frame/schedule/MCU response)
├── protocol/                 # Protocol command contract JSON
├── configs/                  # Runtime + bench + geometry + calibration configs
├── docs/openspec/v3/         # Versioned OpenSpec mirrors and compliance docs
├── data/                     # Data manifest
├── tools/                    # Utility scripts (e.g., readiness reporting)
├── README.md
├── architecture.md
├── openspec.md
└── pyproject.toml
```

## Fast navigation index
| Task | Primary files |
|---|---|
| Protocol behavior | `src/coloursorter/protocol/*`, `protocol/commands.json` |
| Wire parse/serialize | `src/coloursorter/serial_interface/serial_interface.py`, `src/coloursorter/serial_interface/wire.py` |
| Scheduler output | `src/coloursorter/scheduler/output.py` |
| Bench execution | `src/coloursorter/bench/runner.py`, `src/coloursorter/bench/cli.py` |
| GUI runtime loop | `gui/bench_app/controller.py`, `gui/bench_app/app.py` |
| OpenSpec mirrors | `docs/openspec/v3/**` |
| Tests entry | `tests/test_integration.py` + targeted module tests |
