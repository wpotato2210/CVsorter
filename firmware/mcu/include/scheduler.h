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
bool scheduler_should_trigger(int32_t current_tick, int32_t target_tick);

#endif
