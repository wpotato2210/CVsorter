# MCU Target Constraints (Arduino / ESP32 / Raspberry Pi Pico)

Authoritative board-level assumptions for firmware generation readiness.

## Electrical and interface matrix

| Target | Logic level | Supply notes | UART pins (default) | PWM-capable outputs (recommended) | Driver requirements |
|---|---|---|---|---|---|
| Arduino Uno (ATmega328P) | 5V GPIO (3.3V tolerated only on input with care) | 5V MCU rail; isolate motor/servo rail from logic rail | D0 (RX), D1 (TX) | D3, D5, D6, D9, D10, D11 | Use transistor/MOSFET or relay driver stage; do not drive relay/motor coil from GPIO directly. |
| ESP32 DevKit (WROOM32) | 3.3V GPIO only | 3.3V logic, 5V USB input; level shift for 5V peripherals | GPIO3 (RX0), GPIO1 (TX0) or remapped UART2 pins | LEDC PWM on most output-capable GPIOs | Use 3.3V-safe drivers or level shifters; separate actuator power and common ground reference. |
| Raspberry Pi Pico (RP2040) | 3.3V GPIO only | 3.3V logic; VSYS 1.8–5.5V input | UART0: GP0 (TX), GP1 (RX) default | PWM slices on most GPIO pins | Use external transistor/MOSFET/relay drivers; no direct inductive load from GPIO. |

## Safety and protection requirements

- Flyback diode required for inductive loads (relay, solenoid, motor) at driver output stage.
- Shared ground required between MCU logic and external driver board.
- Brownout handling must force SAFE path; threshold reference: `FW_BROWNOUT_MIN_MV` in `firmware/mcu/config/firmware_config.h`.
- Watchdog timeout must transition to SAFE and clear queue (`FW_WATCHDOG_PERIOD_MS`).

## Timing and scheduler constraints

- Scheduler tick target: `FW_SCHEDULER_TICK_US = 1000` (1 kHz baseline).
- ISR service budgets: UART `FW_ISR_UART_BUDGET_US = 20`, timer `FW_ISR_TIMER_BUDGET_US = 10`.
- Queue depth cap: `FW_QUEUE_DEPTH_MAX = 8` aligned with OpenSpec queue contract.
- Host command bounds: lane `0..21`, trigger `0.0..2000.0 mm`.

## Firmware generation readiness requirement

- `.ino` generation is allowed only when board pin assignment, logic-level compatibility, and actuator driver stage are declared for the chosen target board profile.
