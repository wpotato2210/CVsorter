# Serial Protocol Trace Examples

## 1) Normal ACK Flow

```text
HOST -> MCU: <SCHED|2|345.500>
MCU  -> HOST: <ACK>
HOST -> MCU: <GET_STATE>
MCU  -> HOST: <ACK|mode=AUTO|queue_depth=1|scheduler_state=ARMED>
```

## 2) Timeout + Retry Flow

```text
HOST -> MCU: <SET_MODE|AUTO>
HOST    wait: 100 ms (timeout)
HOST -> MCU: <SET_MODE|AUTO>   # retry 1
HOST    wait: 100 ms (timeout)
HOST -> MCU: <SET_MODE|AUTO>   # retry 2
MCU  -> HOST: <ACK>
```

Policy: max 3 retries with backoff delays `[0, 50, 100]` ms.

## 3) NACK Flow (Range Error)

```text
HOST -> MCU: <SCHED|9|100.000>
MCU  -> HOST: <NACK|3|lane out of range [0,7]>
HOST -> MCU: <SCHED|7|100.000>
MCU  -> HOST: <ACK>
```

NACK code `3` maps to `ARG_RANGE_ERROR`.

## 4) SAFE Transition Auto-Clear Flow

```text
HOST -> MCU: <SCHED|1|100.000>
MCU  -> HOST: <ACK>
HOST -> MCU: <SET_MODE|SAFE>
MCU  -> HOST: <ACK|mode=SAFE|queue_depth=0|queue_cleared=true|scheduler_state=SAFE>
```

Entering `SAFE` always clears pending queue entries.
