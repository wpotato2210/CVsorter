#include "command_dispatch.h"

#include <assert.h>

#include "scheduler.h"

int main(void) {
  fw_runtime_state_t runtime;
  fw_response_t response;

  scheduler_init();
  fw_runtime_init(&runtime);

  fw_dispatch_command(&runtime, &(fw_command_t){.type = FW_CMD_HELLO}, &response);
  assert(response.status == FW_STATUS_OK);
  assert(response.state.link_state == FW_LINK_UP);

  fw_dispatch_command(&runtime,
                      &(fw_command_t){.type = FW_CMD_HEARTBEAT,
                                      .payload.heartbeat_id = 42U},
                      &response);
  assert(response.status == FW_STATUS_OK);
  assert(response.heartbeat_id == 42U);

  fw_dispatch_command(&runtime,
                      &(fw_command_t){.type = FW_CMD_SET_MODE,
                                      .payload.mode = FW_MODE_RUN},
                      &response);
  assert(response.status == FW_STATUS_OK);
  assert(response.state.mode == FW_MODE_RUN);

  fw_dispatch_command(&runtime,
                      &(fw_command_t){.type = FW_CMD_SCHED,
                                      .payload.slot = {.lane = 1U, .trigger_mm = 120U}},
                      &response);
  assert(response.status == FW_STATUS_OK);
  assert(response.state.queue_depth == 1U);
  assert(response.state.scheduler_state == FW_SCHEDULER_RUNNING);

  fw_dispatch_command(&runtime, &(fw_command_t){.type = FW_CMD_GET_STATE}, &response);
  assert(response.status == FW_STATUS_OK);
  assert(response.state.queue_depth == 1U);

  fw_dispatch_command(&runtime, &(fw_command_t){.type = FW_CMD_RESET_QUEUE}, &response);
  assert(response.status == FW_STATUS_OK);
  assert(response.state.queue_depth == 0U);
  assert(response.state.scheduler_state == FW_SCHEDULER_IDLE);

  return 0;
}
