#include <assert.h>
#include <stdbool.h>
#include <stdint.h>

#include "encoder.h"
#include "queue.h"
#include "safety.h"
#include "scheduler.h"

static void test_encoder_module(void) {
  encoder_reset();
  assert(encoder_ticks == 0);

  encoder_isr_on_tick(1, 10U);
  encoder_isr_on_tick(1, 20U);
  encoder_isr_on_tick(-1, 25U);

  assert(encoder_ticks == 1);
  assert(last_tick_time_ms == 25U);
  assert(encoder_check_timeout(30U, 10U) == false);
  assert(encoder_check_timeout(40U, 10U) == true);
}

static void test_queue_module(void) {
  queue_clear();
  assert(queue_size() == 0U);

  assert(queue_push((event_t){.lane = 2U, .trigger_tick = 30}));
  assert(queue_push((event_t){.lane = 1U, .trigger_tick = 10}));
  assert(queue_push((event_t){.lane = 3U, .trigger_tick = 20}));

  event_t top = {0};
  assert(queue_peek(&top));
  assert(top.trigger_tick == 10);
  assert(queue_size() == 3U);

  event_t out = {0};
  assert(queue_pop(&out) && out.trigger_tick == 10);
  assert(queue_pop(&out) && out.trigger_tick == 20);
  assert(queue_pop(&out) && out.trigger_tick == 30);
  assert(queue_pop(&out) == false);

  queue_clear();
  for (uint16_t i = 0U; i < QUEUE_CAPACITY; ++i) {
    assert(queue_push((event_t){.lane = 0U, .trigger_tick = (int32_t)i}));
  }
  assert(queue_push((event_t){.lane = 0U, .trigger_tick = 9999}) == false);
  queue_clear();
  assert(queue_size() == 0U);
}

static void test_scheduler_module(void) {
  queue_clear();
  safety_clear_safe();
  encoder_reset();
  encoder_ticks = 100;

  assert(scheduler_schedule(1U, 2.0f));

  event_t event = {0};
  assert(queue_peek(&event));
  assert(event.lane == 1U);
  assert(event.trigger_tick == 124);

  assert(scheduler_should_trigger(200, 124));
  assert(!scheduler_should_trigger(123, 124));

  safety_enter_safe(FAULT_BROWNOUT);
  assert(!scheduler_schedule(1U, 1.0f));
  safety_clear_safe();
}

static void test_safety_module(void) {
  safety_clear_safe();
  queue_clear();

  const fault_reason_t reasons[] = {
      FAULT_QUEUE_OVERFLOW,
      FAULT_ENCODER_TIMEOUT,
      FAULT_BROWNOUT,
      FAULT_SERIAL_OVERFLOW,
  };

  for (uint32_t i = 0; i < (sizeof(reasons) / sizeof(reasons[0])); ++i) {
    queue_push((event_t){.lane = 0U, .trigger_tick = 1});
    assert(queue_size() == 1U);

    safety_enter_safe(reasons[i]);
    assert(safety_is_safe());
    assert(!safety_servos_enabled());
    assert(safety_last_fault() == reasons[i]);
    assert(queue_size() == 0U);

    safety_clear_safe();
    assert(!safety_is_safe());
    assert(safety_servos_enabled());
    assert(safety_last_fault() == FAULT_NONE);
  }
}

int main(void) {
  test_encoder_module();
  test_queue_module();
  test_scheduler_module();
  test_safety_module();
  return 0;
}
