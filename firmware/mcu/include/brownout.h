#ifndef COLOURSORTER_BROWNOUT_H
#define COLOURSORTER_BROWNOUT_H

#include <stdbool.h>
#include <stdint.h>

void brownout_init(uint32_t min_mv);
bool brownout_trip(uint32_t supply_mv);

#endif
