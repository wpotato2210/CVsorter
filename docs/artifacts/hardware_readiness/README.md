# Hardware Readiness Artifacts

This directory stores checked-in evidence for `docs/hardware_readiness_gate.md`.

Expected structure:

- `protocol/` protocol traces and interoperability summary
- `queue/` queue stress logs and summary
- `safety/` SAFE/watchdog fault-injection logs and summary
- `timing/` timing budget exports and summary

Run `python tools/hardware_readiness_report.py` to summarize completeness.
