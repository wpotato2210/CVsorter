#include "safety.h"

#include "queue.h"

static bool s_is_safe = false;
static fault_reason_t s_last_fault = FAULT_NONE;
static bool s_servos_enabled = true;

void safety_enter_safe(fault_reason_t reason) {
  s_is_safe = true;
  s_last_fault = reason;
  s_servos_enabled = false;
  queue_clear();
}

void safety_clear_safe(void) {
  s_is_safe = false;
  s_last_fault = FAULT_NONE;
  s_servos_enabled = true;
}

bool safety_is_safe(void) {
  return s_is_safe;
}

fault_reason_t safety_last_fault(void) {
  return s_last_fault;
}

bool safety_servos_enabled(void) {
  return s_servos_enabled;
}
