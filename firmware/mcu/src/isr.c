#include "isr.h"

#include <stddef.h>

static volatile uint32_t s_tick_count = 0U;
static volatile uint8_t s_uart_shadow = 0U;

/* Timing annotation: UART ISR budget 20 us per byte, no dynamic memory */
void isr_uart_rx_byte(uint8_t byte_value) {
  s_uart_shadow = byte_value;
  (void)s_uart_shadow;
}

/* Timing annotation: timer ISR budget 10 us at 1 kHz */
void isr_scheduler_tick(void) {
  s_tick_count += 1U;
}
