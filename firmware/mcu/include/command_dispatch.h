#ifndef COLOURSORTER_COMMAND_DISPATCH_H
#define COLOURSORTER_COMMAND_DISPATCH_H

#include <stdint.h>

#include "scheduler.h"

typedef enum {
  FW_MODE_SAFE = 0,
  FW_MODE_RUN = 1,
  FW_MODE_SERVICE = 2,
} fw_mode_t;

typedef enum {
  FW_SCHEDULER_IDLE = 0,
  FW_SCHEDULER_RUNNING = 1,
} fw_scheduler_state_t;

typedef enum {
  FW_LINK_DOWN = 0,
  FW_LINK_UP = 1,
} fw_link_state_t;

typedef struct {
  fw_mode_t mode;
  uint8_t queue_depth;
  fw_scheduler_state_t scheduler_state;
  fw_link_state_t link_state;
} fw_runtime_state_t;

typedef enum {
  FW_CMD_HELLO = 0,
  FW_CMD_HEARTBEAT = 1,
  FW_CMD_SET_MODE = 2,
  FW_CMD_SCHED = 3,
  FW_CMD_GET_STATE = 4,
  FW_CMD_RESET_QUEUE = 5,
} fw_command_type_t;

typedef struct {
  fw_command_type_t type;
  union {
    fw_mode_t mode;
    scheduler_slot_t slot;
    uint32_t heartbeat_id;
  } payload;
} fw_command_t;

typedef enum {
  FW_STATUS_OK = 0,
  FW_STATUS_INVALID_MODE = 1,
  FW_STATUS_QUEUE_FULL = 2,
  FW_STATUS_INVALID_COMMAND = 3,
} fw_status_t;

typedef struct {
  fw_status_t status;
  uint32_t heartbeat_id;
  fw_runtime_state_t state;
} fw_response_t;

void fw_runtime_init(fw_runtime_state_t *runtime_state);
void fw_dispatch_command(
    fw_runtime_state_t *runtime_state,
    const fw_command_t *command,
    fw_response_t *response);

#endif
