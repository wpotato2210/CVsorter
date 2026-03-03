# Hardware Readiness Gate

This checklist defines the minimum evidence required before declaring a release hardware-ready.

## Acceptance criteria and evidence mapping

| Gate criterion | Acceptance threshold | Primary test/artifact source | Required output location(s) |
|---|---|---|---|
| Protocol interoperability with OpenSpec v3 command surface (`SET_MODE`, `SCHED`, `GET_STATE`, `RESET_QUEUE`) | 100% pass on required commands with no unsupported frame variants during bench replay and hardware probe | Protocol compliance test logs and captured protocol traces from bench and hardware sessions | `docs/artifacts/hardware_readiness/protocol/bench_protocol_trace.log`, `docs/artifacts/hardware_readiness/protocol/hardware_protocol_trace.log`, `docs/artifacts/hardware_readiness/protocol/protocol_interop_summary.md` |
| Queue behavior under nominal and saturation load | Zero dropped commands before queue-full boundary; queue-full behavior must emit expected NACK and recover after dequeue/reset | Bench queue stress logs and hardware queue stress serial captures | `docs/artifacts/hardware_readiness/queue/bench_queue_stress.log`, `docs/artifacts/hardware_readiness/queue/hardware_queue_stress.log`, `docs/artifacts/hardware_readiness/queue/queue_behavior_summary.md` |
| SAFE/watchdog recovery path | All injected watchdog/time-out fault scenarios must converge to SAFE and recover through documented MANUAL-to-AUTO flow without process restart | Serial fault injection logs and controller recovery trace captures from bench + hardware | `docs/artifacts/hardware_readiness/safety/bench_fault_injection.log`, `docs/artifacts/hardware_readiness/safety/hardware_fault_injection.log`, `docs/artifacts/hardware_readiness/safety/safe_watchdog_recovery_summary.md` |
| Timing budget conformance | P95 and max cycle/stage latencies within OpenSpec v3 timing budget limits for bench and hardware runs | Timing budget benchmark exports, telemetry CSV snapshots, and roll-up analysis note | `docs/artifacts/hardware_readiness/timing/bench_timing_budget.csv`, `docs/artifacts/hardware_readiness/timing/hardware_timing_budget.csv`, `docs/artifacts/hardware_readiness/timing/timing_budget_summary.md` |

## Review workflow

1. Collect artifacts in the required output locations above.
2. Run `python tools/hardware_readiness_report.py --strict`.
3. Run `python tools/firmware_readiness_check.py --strict`.
4. Confirm board profile constraints are documented in `docs/mcu_target_constraints.md` for the selected MCU target.
5. Attach both report outputs to the release review thread.
6. Mark release as finished only when all criteria report `PASS`.

## CI usage

- Non-blocking summary: `python tools/hardware_readiness_report.py`
- Blocking gate: `python tools/hardware_readiness_report.py --strict`
- CI/release blocking workflow: `.github/workflows/hardware-readiness-gate.yml` runs `python tools/hardware_readiness_report.py --strict` on pull requests, `main` pushes, and published releases.

- Additional firmware readiness gate: `python tools/firmware_readiness_check.py --strict` validates protocol/schema/config parity for firmware generation.
