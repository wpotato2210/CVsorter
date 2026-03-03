#include "scheduler.h"

#include "firmware_config.h"

static scheduler_slot_t s_queue[FW_QUEUE_DEPTH_MAX];
static uint8_t s_head = 0U;
static uint8_t s_tail = 0U;
static uint8_t s_depth = 0U;

void scheduler_init(void) {
  s_head = 0U;
  s_tail = 0U;
  s_depth = 0U;
}

/* Timing annotation: enqueue called from command executor, <= 4 us WCET */
bool scheduler_enqueue(scheduler_slot_t slot) {
  if (s_depth >= FW_QUEUE_DEPTH_MAX) {
    return false;
  }
  s_queue[s_tail] = slot;
  s_tail = (uint8_t)((s_tail + 1U) % FW_QUEUE_DEPTH_MAX);
  s_depth += 1U;
  return true;
}

/* Timing annotation: dequeue called from actuator task, <= 4 us WCET */
bool scheduler_dequeue(scheduler_slot_t *slot_out) {
  if (s_depth == 0U || slot_out == NULL) {
    return false;
  }
  *slot_out = s_queue[s_head];
  s_head = (uint8_t)((s_head + 1U) % FW_QUEUE_DEPTH_MAX);
  s_depth -= 1U;
  return true;
}

uint8_t scheduler_depth(void) {
  return s_depth;
}
