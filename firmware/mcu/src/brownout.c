#include "brownout.h"

static uint32_t s_min_supply_mv = 0U;

void brownout_init(uint32_t min_mv) {
  s_min_supply_mv = min_mv;
}

/* Timing annotation: sampled each 10 ms in control loop, <= 1 us WCET */
bool brownout_trip(uint32_t supply_mv) {
  return supply_mv < s_min_supply_mv;
}
