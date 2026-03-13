#ifndef COLOURSORTER_SCHEDULER_H
#define COLOURSORTER_SCHEDULER_H

#include <stdbool.h>
#include <stdint.h>

#include "queue.h"

typedef struct {
  uint8_t lane;
  uint16_t trigger_mm;
} scheduler_slot_t;

void scheduler_init(void);
bool scheduler_enqueue(scheduler_slot_t slot);
bool scheduler_dequeue(scheduler_slot_t *slot_out);
uint8_t scheduler_depth(void);
void scheduler_reset(void);

bool scheduler_schedule(uint8_t lane, float position_mm);
typedef enum {
  DISPATCH_RESULT_NONE = 0,
  DISPATCH_RESULT_EXECUTED = 1,
  DISPATCH_RESULT_MISSED_WINDOW = 2,
  DISPATCH_RESULT_SAFE_BLOCKED = 3,
} dispatch_result_t;

bool scheduler_should_trigger(int32_t current_tick, int32_t target_tick);
dispatch_result_t scheduler_dispatch_ready_slot(int32_t current_tick, uint8_t *lane_out);

#endif
