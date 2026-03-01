# Config Enum Migration (Legacy -> Canonical v4)

| Field | Legacy value | Canonical v4 value |
|---|---|---|
| `motion_mode` | `ENCODER` | `FOLLOW_BELT` |
| `motion_mode` | `TIME` | `TIME_WINDOW` |
| `motion_mode` | `MANUAL` | `MANUAL` |
| `homing_mode` | `ENABLED` | `AUTO_HOME` |
| `homing_mode` | `DISABLED` | `SKIP_HOME` |

Startup config and live update handlers now reject values not in canonical v4 enums.
