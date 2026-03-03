#ifndef COLOURSORTER_WATCHDOG_H
#define COLOURSORTER_WATCHDOG_H

#include <stdbool.h>
#include <stdint.h>

void watchdog_init(uint32_t period_ms);
void watchdog_kick(void);
bool watchdog_expired(uint32_t now_ms);

#endif
