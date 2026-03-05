#include "command_dispatch.h"

#include <stddef.h>

static void apply_state_snapshot(
    const fw_runtime_state_t *runtime_state,
    fw_response_t *response) {
  if (response == NULL || runtime_state == NULL) {
    return;
  }
  response->state = *runtime_state;
}

void fw_runtime_init(fw_runtime_state_t *runtime_state) {
  if (runtime_state == NULL) {
    return;
  }

  runtime_state->mode = FW_MODE_SAFE;
  runtime_state->queue_depth = 0U;
  runtime_state->scheduler_state = FW_SCHEDULER_IDLE;
  runtime_state->link_state = FW_LINK_DOWN;
}

void fw_dispatch_command(
    fw_runtime_state_t *runtime_state,
    const fw_command_t *command,
    fw_response_t *response) {
  if (runtime_state == NULL || command == NULL || response == NULL) {
    return;
  }

  response->status = FW_STATUS_OK;
  response->heartbeat_id = 0U;

  switch (command->type) {
    case FW_CMD_HELLO:
      runtime_state->link_state = FW_LINK_UP;
      break;

    case FW_CMD_HEARTBEAT:
      runtime_state->link_state = FW_LINK_UP;
      response->heartbeat_id = command->payload.heartbeat_id;
      break;

    case FW_CMD_SET_MODE:
      if (command->payload.mode > FW_MODE_SERVICE) {
        response->status = FW_STATUS_INVALID_MODE;
      } else {
        runtime_state->mode = command->payload.mode;
      }
      break;

    case FW_CMD_SCHED:
      if (!scheduler_enqueue(command->payload.slot)) {
        response->status = FW_STATUS_QUEUE_FULL;
      }
      runtime_state->queue_depth = scheduler_depth();
      runtime_state->scheduler_state =
          runtime_state->queue_depth == 0U ? FW_SCHEDULER_IDLE : FW_SCHEDULER_RUNNING;
      break;

    case FW_CMD_GET_STATE:
      runtime_state->queue_depth = scheduler_depth();
      runtime_state->scheduler_state =
          runtime_state->queue_depth == 0U ? FW_SCHEDULER_IDLE : FW_SCHEDULER_RUNNING;
      break;

    case FW_CMD_RESET_QUEUE:
      scheduler_reset();
      runtime_state->queue_depth = 0U;
      runtime_state->scheduler_state = FW_SCHEDULER_IDLE;
      break;

    default:
      response->status = FW_STATUS_INVALID_COMMAND;
      break;
  }

  apply_state_snapshot(runtime_state, response);
}
