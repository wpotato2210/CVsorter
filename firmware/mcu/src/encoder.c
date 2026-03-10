#include "encoder.h"

volatile int32_t encoder_ticks = 0;
volatile uint32_t last_tick_time_ms = 0U;

void encoder_reset(void) {
  encoder_ticks = 0;
  last_tick_time_ms = 0U;
}

/* ISR-safe: integer state updates only. */
void encoder_isr_on_tick(int8_t direction, uint32_t now_ms) {
  if (direction >= 0) {
    encoder_ticks += 1;
  } else {
    encoder_ticks -= 1;
  }
  last_tick_time_ms = now_ms;
}

bool encoder_check_timeout(uint32_t now_ms, uint32_t timeout_ms) {
  return (uint32_t)(now_ms - last_tick_time_ms) > timeout_ms;
}
