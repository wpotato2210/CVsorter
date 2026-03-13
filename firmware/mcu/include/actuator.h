#ifndef COLOURSORTER_ACTUATOR_H
#define COLOURSORTER_ACTUATOR_H

#include <stdbool.h>
#include <stdint.h>

void actuator_init(void);
void actuator_emit_pulse(uint8_t lane, uint16_t pulse_width_ms);
bool actuator_last_command(uint8_t *lane_out, uint16_t *pulse_width_ms_out);

#endif
