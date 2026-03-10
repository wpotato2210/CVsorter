#ifndef COLOURSORTER_SAFETY_H
#define COLOURSORTER_SAFETY_H

#include <stdbool.h>

typedef enum {
  FAULT_NONE = 0,
  FAULT_QUEUE_OVERFLOW = 1,
  FAULT_ENCODER_TIMEOUT = 2,
  FAULT_BROWNOUT = 3,
  FAULT_SERIAL_OVERFLOW = 4,
} fault_reason_t;

void safety_enter_safe(fault_reason_t reason);
void safety_clear_safe(void);
bool safety_is_safe(void);
fault_reason_t safety_last_fault(void);
bool safety_servos_enabled(void);

#endif
