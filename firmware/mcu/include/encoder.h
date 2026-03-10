#ifndef COLOURSORTER_ENCODER_H
#define COLOURSORTER_ENCODER_H

#include <stdbool.h>
#include <stdint.h>

extern volatile int32_t encoder_ticks;
extern volatile uint32_t last_tick_time_ms;

void encoder_reset(void);
void encoder_isr_on_tick(int8_t direction, uint32_t now_ms);
bool encoder_check_timeout(uint32_t now_ms, uint32_t timeout_ms);

#endif
