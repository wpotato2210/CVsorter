#ifndef COLOURSORTER_QUEUE_H
#define COLOURSORTER_QUEUE_H

#include <stdbool.h>
#include <stdint.h>

#define QUEUE_CAPACITY 512U

typedef struct {
  uint8_t lane;
  int32_t trigger_tick;
} event_t;

bool queue_push(event_t e);
bool queue_pop(event_t *out);
bool queue_peek(event_t *out);
uint16_t queue_size(void);
void queue_clear(void);

#endif
