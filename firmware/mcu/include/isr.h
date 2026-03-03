#ifndef COLOURSORTER_ISR_H
#define COLOURSORTER_ISR_H

#include <stdint.h>

void isr_uart_rx_byte(uint8_t byte_value);
void isr_scheduler_tick(void);

#endif
