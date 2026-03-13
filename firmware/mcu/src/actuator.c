#include "actuator.h"

#include <stddef.h>

static bool s_has_command = false;
static uint8_t s_last_lane = 0U;
static uint16_t s_last_pulse_width_ms = 0U;

void actuator_init(void) {
  s_has_command = false;
  s_last_lane = 0U;
  s_last_pulse_width_ms = 0U;
}

void actuator_emit_pulse(uint8_t lane, uint16_t pulse_width_ms) {
  s_has_command = true;
  s_last_lane = lane;
  s_last_pulse_width_ms = pulse_width_ms;
}

bool actuator_last_command(uint8_t *lane_out, uint16_t *pulse_width_ms_out) {
  if (!s_has_command || lane_out == NULL || pulse_width_ms_out == NULL) {
    return false;
  }
  *lane_out = s_last_lane;
  *pulse_width_ms_out = s_last_pulse_width_ms;
  return true;
}
