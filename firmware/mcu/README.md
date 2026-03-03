# MCU Firmware Project

Dedicated MCU firmware workspace for OpenSpec v3 command execution.

## Version pinning
- CMake: 3.27.7
- arm-none-eabi-gcc: 13.2.0
- newlib: 4.3.0

Version pins are enforced by:
- `toolchain.lock`
- `cmake/version_pin.cmake`

## Build
```bash
cmake -S firmware/mcu -B firmware/mcu/build
cmake --build firmware/mcu/build
```

## Target constraints
- Board-level constraints and pin/electrical assumptions: `docs/mcu_target_constraints.md`.
- Run firmware readiness parity checks: `python tools/firmware_readiness_check.py --strict`.
