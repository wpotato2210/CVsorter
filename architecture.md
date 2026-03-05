# architecture.md

## Deterministic module chain
`preprocess -> dataset -> model -> train/eval/infer -> scheduler -> actuator_iface`

## Configuration authority
All physical parameters are config-owned under `src/coloursorter/config/*` and consumed read-only by runtime modules.

## Real-time envelope
- `fps_target=100`
- End-to-end `pipeline_latency_ms<=15`
- Queue bounded to `queue_depth=8`
- Heartbeat watchdog: `heartbeat_period_ms<=50`, `heartbeat_timeout_ms<=150`

## Safety control plane
- E-STOP raises `ESTOP_ACTIVE` and `SAFE_LATCH`.
- Scheduler and actuator interface reject motion while latch is active.
- Recovery requires authenticated reset authority workflow.
