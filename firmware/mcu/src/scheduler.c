#include "scheduler.h"

#include <stddef.h>

#include "firmware_config.h"
#include "safety.h"

#if defined(__GNUC__)
extern volatile int32_t encoder_ticks __attribute__((weak));
extern bool safety_is_safe(void) __attribute__((weak));
extern void safety_enter_safe(fault_reason_t reason) __attribute__((weak));
#else
extern volatile int32_t encoder_ticks;
extern bool safety_is_safe(void);
extern void safety_enter_safe(fault_reason_t reason);
#endif

#ifndef FW_SCHEDULER_LANE_MAX
#define FW_SCHEDULER_LANE_MAX 8U
#endif

#ifndef FW_ENCODER_TICKS_PER_MM
#define FW_ENCODER_TICKS_PER_MM 10U
#endif

static const int16_t k_lane_comp_ticks[FW_SCHEDULER_LANE_MAX] = {0, 4, 8, 12, 16, 20, 24, 28};

void scheduler_init(void) { queue_clear(); }

bool scheduler_enqueue(scheduler_slot_t slot) {
  event_t event = {.lane = slot.lane, .trigger_tick = (int32_t)slot.trigger_mm};
  return queue_push(event);
}

bool scheduler_dequeue(scheduler_slot_t *slot_out) {
  event_t event;
  if (slot_out == NULL || !queue_pop(&event)) {
    return false;
  }
  slot_out->lane = event.lane;
  if (event.trigger_tick < 0) {
    slot_out->trigger_mm = 0U;
  } else if (event.trigger_tick > 65535) {
    slot_out->trigger_mm = 65535U;
  } else {
    slot_out->trigger_mm = (uint16_t)event.trigger_tick;
  }
  return true;
}

uint8_t scheduler_depth(void) {
  uint16_t size = queue_size();
  return (size > 255U) ? 255U : (uint8_t)size;
}

void scheduler_reset(void) { queue_clear(); }

static bool scheduler_safe_state(void) {
  return (safety_is_safe != NULL) ? safety_is_safe() : false;
}

static void scheduler_raise_overflow_fault(void) {
  if (safety_enter_safe != NULL) {
    safety_enter_safe(FAULT_QUEUE_OVERFLOW);
  }
}

bool scheduler_schedule(uint8_t lane, float position_mm) {
  if (scheduler_safe_state()) {
    return false;
  }
  if (lane >= FW_SCHEDULER_LANE_MAX || position_mm < 0.0f) {
    return false;
  }

  int32_t base_tick = (&encoder_ticks != NULL) ? encoder_ticks : 0;
  int32_t delta_ticks = (int32_t)(position_mm * (float)FW_ENCODER_TICKS_PER_MM);
  int32_t target_tick = base_tick + delta_ticks + k_lane_comp_ticks[lane];

  if (!queue_push((event_t){.lane = lane, .trigger_tick = target_tick})) {
    scheduler_raise_overflow_fault();
    return false;
  }
  return true;
}

bool scheduler_should_trigger(int32_t current_tick, int32_t target_tick) {
  return (int32_t)(current_tick - target_tick) >= 0;
}
