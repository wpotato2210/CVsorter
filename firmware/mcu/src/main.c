#include "brownout.h"
#include "firmware_config.h"
#include "scheduler.h"
#include "watchdog.h"

int main(void) {
  watchdog_init(FW_WATCHDOG_PERIOD_MS);
  brownout_init(FW_BROWNOUT_MIN_MV);
  scheduler_init();

  for (;;) {
    watchdog_kick();
  }
}
