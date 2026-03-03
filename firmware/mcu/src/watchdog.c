#include "watchdog.h"

static uint32_t s_period_ms = 0U;
static uint32_t s_last_kick_ms = 0U;

void watchdog_init(uint32_t period_ms) {
  s_period_ms = period_ms;
  s_last_kick_ms = 0U;
}

/* Timing annotation: called every scheduler tick (1 ms), <= 2 us WCET */
void watchdog_kick(void) {
  s_last_kick_ms += 1U;
}

/* Timing annotation: evaluated from main loop, <= 1 us WCET */
bool watchdog_expired(uint32_t now_ms) {
  return (now_ms - s_last_kick_ms) > s_period_ms;
}
