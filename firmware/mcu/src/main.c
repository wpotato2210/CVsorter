#include "brownout.h"
#include "command_dispatch.h"
#include "firmware_config.h"
#include "scheduler.h"
#include "watchdog.h"
#include "actuator.h"

static fw_runtime_state_t s_runtime_state;

static void process_command(const fw_command_t *command) {
  fw_response_t response;
  fw_dispatch_command(&s_runtime_state, command, &response);
  (void)response;
}

int main(void) {
  watchdog_init(FW_WATCHDOG_PERIOD_MS);
  brownout_init(FW_BROWNOUT_MIN_MV);
  scheduler_init();
  actuator_init();
  fw_runtime_init(&s_runtime_state);

  process_command(&(fw_command_t){.type = FW_CMD_HELLO});

  for (;;) {
    uint8_t lane = 0U;
    dispatch_result_t dispatch_result = scheduler_dispatch_ready_slot(0, &lane);
    if (dispatch_result == DISPATCH_RESULT_EXECUTED) {
      actuator_emit_pulse(lane, FW_ACTUATION_PULSE_WIDTH_MS);
    }
    watchdog_kick();
  }
}
