#include <gtest/gtest.h>

extern "C" {
#include "command_dispatch.h"
#include "encoder.h"
#include "safety.h"
#include "scheduler.h"
#include "watchdog.h"
}

TEST(FirmwareSchedulerTest, QueueOrderAndDepthAreDeterministic) {
  scheduler_init();

  scheduler_slot_t first{.lane = 1, .trigger_mm = 100};
  scheduler_slot_t second{.lane = 2, .trigger_mm = 200};

  EXPECT_TRUE(scheduler_enqueue(first));
  EXPECT_TRUE(scheduler_enqueue(second));
  EXPECT_EQ(scheduler_depth(), 2);

  scheduler_slot_t out{};
  ASSERT_TRUE(scheduler_dequeue(&out));
  EXPECT_EQ(out.lane, 1);
  EXPECT_EQ(out.trigger_mm, 100);

  ASSERT_TRUE(scheduler_dequeue(&out));
  EXPECT_EQ(out.lane, 2);
  EXPECT_EQ(out.trigger_mm, 200);
  EXPECT_EQ(scheduler_depth(), 0);
}

TEST(FirmwareDispatchTest, HelloHeartbeatAndSchedUpdateRuntimeState) {
  scheduler_reset();

  fw_runtime_state_t runtime{};
  fw_runtime_init(&runtime);
  fw_response_t response{};

  fw_command_t hello{.type = FW_CMD_HELLO};
  fw_dispatch_command(&runtime, &hello, &response);
  EXPECT_EQ(response.status, FW_STATUS_OK);
  EXPECT_EQ(response.state.link_state, FW_LINK_UP);

  fw_command_t heartbeat{.type = FW_CMD_HEARTBEAT};
  heartbeat.payload.heartbeat_id = 42;
  fw_dispatch_command(&runtime, &heartbeat, &response);
  EXPECT_EQ(response.status, FW_STATUS_OK);
  EXPECT_EQ(response.heartbeat_id, 42U);

  fw_command_t sched{.type = FW_CMD_SCHED};
  sched.payload.slot = scheduler_slot_t{.lane = 3, .trigger_mm = 333};
  fw_dispatch_command(&runtime, &sched, &response);

  EXPECT_EQ(response.status, FW_STATUS_OK);
  EXPECT_EQ(response.state.queue_depth, 1);
  EXPECT_EQ(response.state.scheduler_state, FW_SCHEDULER_RUNNING);
}

TEST(FirmwareWatchdogTest, ExpiryWithoutBlockingDelay) {
  watchdog_init(3);

  EXPECT_FALSE(watchdog_expired(0));
  watchdog_kick();
  watchdog_kick();
  EXPECT_FALSE(watchdog_expired(4));
  EXPECT_TRUE(watchdog_expired(6));
}

TEST(FirmwareSchedulerPhase32Test, ScheduleUsesDeterministicTickMathAndLaneCompensation) {
  scheduler_reset();
  safety_clear_safe();
  encoder_ticks = 1'000;

  ASSERT_TRUE(scheduler_schedule(2, 5.0F));
  EXPECT_EQ(scheduler_depth(), 1);

  scheduler_slot_t out{};
  ASSERT_TRUE(scheduler_dequeue(&out));
  EXPECT_EQ(out.lane, 2);
  EXPECT_EQ(out.trigger_mm, 1'058);
}

TEST(FirmwareSchedulerPhase32Test, ScheduleIsSafeModeGatedAndQueueRemainsUnchanged) {
  scheduler_reset();
  safety_enter_safe(FAULT_BROWNOUT);

  EXPECT_FALSE(scheduler_schedule(1, 3.0F));
  EXPECT_EQ(scheduler_depth(), 0);

  safety_clear_safe();
}
