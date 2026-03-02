# GUI POC Audit Report — `controller_integration_stub.py`

## Scope
Bench/webcam GUI POC readiness review for `gui/bench_app/controller_integration_stub.py`, focused on pre-hardware and pre-production CV integration.

## Summary Table

| # | Category | Status | Readiness Notes |
|---|---|---|---|
| 1 | Frame source readiness (webcam + fallback) | PASS | Webcam-first acquisition with deterministic simulated-frame fallback is implemented and non-blocking in normal flow. |
| 2 | Overlay rendering correctness | PASS | Overlay box/text draw path is valid for BGR→RGB conversion and QLabel pixmap scaling. |
| 3 | Frame-indexed logging and `command_log` behavior | PASS | `_frame_index` increments per tick; hit events append structured log entries with telemetry. |
| 4 | Tick loop / event-loop responsiveness | WARNING | QTimer tick path is lightweight, but no timing guard or exception boundary exists for expensive CV/camera failures. |
| 5 | Mock servo / command telemetry integration | PASS | Command dispatch + synthesized telemetry are integrated into status and persistent command log. |
| 6 | Placeholder CV detection reaction | PASS | HSV+contour threshold reliably drives hit/no-hit branching and overlay state in POC assumptions. |
| 7 | Runnable demo behavior | WARNING | `__main__` wiring is correct, but runtime validation in this environment is blocked by missing GUI/OpenGL shared library. |
| 8 | Error / exception handling | WARNING | No explicit try/except around camera read, color conversion, or contour extraction; UI may fail hard on unexpected frame/input states. |

---

## 1) Frame source readiness (webcam + fallback)
**Status: PASS**

- **Observed behavior**
  - `_next_frame()` attempts webcam open lazily on first use via `cv2.VideoCapture(camera_index)`.
  - On successful open, width/height are configured and frames are read each tick.
  - If open/read fails, `_build_simulated_frame()` returns a synthetic BGR frame with moving yellow circle.
- **Issues**
  - If a camera opens but intermittently returns bad frames, there is no explicit retry/backoff telemetry.
- **Recommendations**
  - Add status hints (e.g., `source=webcam|simulated`) to improve operator visibility.
  - Consider periodic re-open attempts if camera read fails N consecutive times.

## 2) Overlay rendering correctness
**Status: PASS**

- **Observed behavior**
  - `show_frame_overlay()` guards non-3D frames.
  - On detection, rectangle + `DETECTED` text are drawn in green.
  - Frame conversion BGR→RGB and QLabel scaling path are correctly ordered.
- **Issues**
  - No explicit handling for zero-size QLabel or detached widget state.
- **Recommendations**
  - Add optional no-op guard if preview label size is empty.
  - Return overlay metadata (bbox/text) to support future testing assertions.

## 3) Frame-indexed logging and `command_log` behavior
**Status: PASS**

- **Observed behavior**
  - `_frame_index` increments each `_tick()`.
  - Detection hit generates entry: frame index + command + telemetry.
  - Entries append to `command_log`; status label mirrors latest event.
  - `enable_logging=True` prints the same entry to console.
- **Issues**
  - Miss events (`detection=none`) are not persisted in `command_log`.
- **Recommendations**
  - Add optional full event log mode including misses for audit/replay.
  - Add cap/rotation for long bench sessions to bound memory.

## 4) Tick loop / event-loop responsiveness
**Status: WARNING**

- **Observed behavior**
  - `QTimer` interval-based loop keeps control flow centralized and easy to reason about.
  - Work per tick is modest (capture/read, thresholding, simple contours, overlay, label updates).
- **Issues**
  - All CV and I/O execute in GUI thread; spikes can cause UI jitter.
  - No watchdog/timeout metrics are captured per tick.
- **Recommendations**
  - Add optional tick duration measurement and warning threshold logging.
  - For heavier CV, move processing to worker thread and marshal UI updates via signals.

## 5) Mock servo / command telemetry integration
**Status: PASS**

- **Observed behavior**
  - On hit, `_send_serial_command("FIRE_TEST")` is called.
  - `_mock_servo_feedback()` returns synthetic position/duty/latency payload.
  - Telemetry is surfaced in status and command log for GUI observability.
- **Issues**
  - No explicit ACK/NAK state machine or command correlation ID.
- **Recommendations**
  - Add monotonically increasing command ID to aid future MCU integration.
  - Introduce mock failure cases (timeout, invalid ACK) for negative-path UI tests.

## 6) Placeholder CV detection reaction
**Status: PASS**

- **Observed behavior**
  - `_simple_detection()` uses HSV threshold `[20,100,100]..[30,255,255]` and contour area gate.
  - Hit path triggers command + telemetry; no-hit path updates status only.
  - Simulated yellow circle should fall inside threshold band, supporting POC demonstrability.
- **Issues**
  - Hardcoded thresholds can be lighting-sensitive and camera-dependent.
- **Recommendations**
  - Externalize HSV + min-area config for bench tuning.
  - Emit lightweight debug counters (`mask_pixels`, `largest_area`) for calibration.

## 7) Runnable demo behavior
**Status: WARNING**

- **Observed behavior**
  - `__main__` creates app/window/controller/integration and starts integration with single-shot timer.
  - `aboutToQuit` hook ensures `stop()` cleanup path runs.
- **Issues**
  - Runtime execution was not fully validated in this container due to missing `libGL.so.1` when importing PySide6 GUI path.
- **Recommendations**
  - Validate on a host with GUI/OpenGL runtime available.
  - Add a minimal CI smoke mode with `QT_QPA_PLATFORM=offscreen` in an image containing required libs.

## 8) Error / exception handling
**Status: WARNING**

- **Observed behavior**
  - Input-shape guard exists in overlay method.
  - Camera release is handled in `stop()`.
- **Issues**
  - No exception boundaries around:
    - `cv2.cvtColor` (overlay/detection),
    - `findContours`,
    - camera read pipeline,
    - GUI pixmap conversion.
  - A raised exception in `_tick()` would likely break periodic processing.
- **Recommendations**
  - Add guarded `_tick()` wrapper with scoped exception logging and continued loop operation.
  - Surface recoverable errors in status label with concise operator-readable code.

---

## Risks & Edge Cases for GUI Testing

- Camera device opens but yields stale/empty frames intermittently.
- Headless/CI hosts missing GUI/OpenGL dependencies (`libGL.so.1`) prevent runtime tests.
- CPU spikes from future CV expansion can degrade timer cadence and perceived UI responsiveness.
- Unbounded `command_log` growth in long soak tests.
- False positives/negatives under lighting variance due to static HSV thresholds.

## Readiness Decision (POC Stage)

- **Overall:** **Conditionally ready** for next POC step.
- **Proceed with:**
  1. Bench calibration hooks (HSV/area configs),
  2. Tick/error instrumentation,
  3. Negative-path telemetry simulation.
- **Before hardware/full CV integration:** add robust exception handling and basic performance counters.
