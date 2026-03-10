#include "serial_protocol.h"

#include <cassert>
#include <cstdint>
#include <cstring>
#include <string>

namespace {

struct FakeScheduler {
  std::uint16_t size = 0U;
  std::uint16_t capacity = 2U;
  std::uint8_t last_lane = 0U;
  std::int32_t last_position = 0;
  std::uint32_t enqueue_calls = 0U;
};

struct FakeEncoder {
  std::int32_t position = 0;
  std::uint32_t zero_calls = 0U;
};

struct FakeParams {
  cvsorter::ProtocolMode mode = cvsorter::ProtocolMode::kTime;
  std::int32_t speed_mm_s = 50;
  std::int32_t reject_ms = 25;
};

struct FakeSafety {
  bool safe_active = false;
  std::uint32_t enter_safe_calls = 0U;
};

struct OutputSink {
  std::string lines;
  std::uint32_t count = 0U;
};

bool scheduler_enqueue(std::uint8_t lane, std::int32_t position_mm, void* context) {
  auto* scheduler = static_cast<FakeScheduler*>(context);
  ++scheduler->enqueue_calls;
  scheduler->last_lane = lane;
  scheduler->last_position = position_mm;
  if (scheduler->size >= scheduler->capacity) {
    return false;
  }
  ++scheduler->size;
  return true;
}

std::uint16_t scheduler_queue_size(void* context) {
  return static_cast<FakeScheduler*>(context)->size;
}

std::int32_t encoder_position(void* context) {
  return static_cast<FakeEncoder*>(context)->position;
}

void encoder_zero(void* context) {
  auto* encoder = static_cast<FakeEncoder*>(context);
  encoder->position = 0;
  ++encoder->zero_calls;
}

bool params_set_mode(cvsorter::ProtocolMode mode, void* context) {
  static_cast<FakeParams*>(context)->mode = mode;
  return true;
}

bool params_set_param(const char* name, std::int32_t value, void* context) {
  auto* params = static_cast<FakeParams*>(context);
  if (std::strcmp(name, "speed_mm_s") == 0) {
    if (value < 10 || value > 300) {
      return false;
    }
    params->speed_mm_s = value;
    return true;
  }
  if (std::strcmp(name, "reject_ms") == 0) {
    if (value < 1 || value > 100) {
      return false;
    }
    params->reject_ms = value;
    return true;
  }
  return false;
}

bool params_get_param(const char* name, std::int32_t* out_value, void* context) {
  auto* params = static_cast<FakeParams*>(context);
  if (std::strcmp(name, "speed_mm_s") == 0) {
    *out_value = params->speed_mm_s;
    return true;
  }
  if (std::strcmp(name, "reject_ms") == 0) {
    *out_value = params->reject_ms;
    return true;
  }
  return false;
}

std::size_t params_list(cvsorter::ParamSnapshot* out_params, std::size_t max_params, void* context) {
  auto* params = static_cast<FakeParams*>(context);
  if (max_params < 2U) {
    return 0U;
  }
  out_params[0] = cvsorter::ParamSnapshot{"reject_ms", params->reject_ms};
  out_params[1] = cvsorter::ParamSnapshot{"speed_mm_s", params->speed_mm_s};
  return 2U;
}

bool safety_is_active(void* context) {
  return static_cast<FakeSafety*>(context)->safe_active;
}

void safety_enter_safe(void* context) {
  auto* safety = static_cast<FakeSafety*>(context);
  safety->safe_active = true;
  ++safety->enter_safe_calls;
}

void safety_clear_safe(void* context) {
  static_cast<FakeSafety*>(context)->safe_active = false;
}

void write_response(const char* response, void* context) {
  auto* sink = static_cast<OutputSink*>(context);
  sink->lines += response;
  sink->lines.push_back('\n');
  ++sink->count;
}

void feed_string(cvsorter::SerialProtocol* protocol, const char* input) {
  const auto* bytes = reinterpret_cast<const std::uint8_t*>(input);
  protocol->ingest_bytes(bytes, std::strlen(input));
}

cvsorter::SerialProtocol build_protocol(FakeScheduler* scheduler,
                                        FakeEncoder* encoder,
                                        FakeParams* params,
                                        FakeSafety* safety,
                                        OutputSink* sink) {
  const cvsorter::SchedulerApi scheduler_api{scheduler_enqueue, scheduler_queue_size, scheduler};
  const cvsorter::EncoderApi encoder_api{encoder_position, encoder_zero, encoder};
  const cvsorter::ParamsApi params_api{params_set_mode, params_set_param, params_get_param, params_list, params};
  const cvsorter::SafetyApi safety_api{safety_is_active, safety_enter_safe, safety_clear_safe, safety};
  return cvsorter::SerialProtocol(4U, scheduler_api, encoder_api, params_api, safety_api, write_response, sink);
}

}  // namespace

int main() {
  {
    FakeScheduler scheduler;
    FakeEncoder encoder;
    FakeParams params;
    FakeSafety safety;
    OutputSink sink;
    auto protocol = build_protocol(&scheduler, &encoder, &params, &safety, &sink);

    feed_string(&protocol, "SCHED:2:150\n");
    protocol.process();
    assert(sink.lines == "OK\n");
    assert(scheduler.last_lane == 2U);
    assert(scheduler.last_position == 150);
  }

  {
    FakeScheduler scheduler;
    FakeEncoder encoder;
    FakeParams params;
    FakeSafety safety;
    safety.safe_active = true;
    OutputSink sink;
    auto protocol = build_protocol(&scheduler, &encoder, &params, &safety, &sink);

    feed_string(&protocol, "SCHED:1:10\n");
    protocol.process();
    assert(sink.lines == "ERR\n");
    assert(scheduler.enqueue_calls == 0U);
  }

  {
    FakeScheduler scheduler;
    FakeEncoder encoder;
    FakeParams params;
    FakeSafety safety;
    OutputSink sink;
    auto protocol = build_protocol(&scheduler, &encoder, &params, &safety, &sink);

    for (std::uint32_t i = 0U; i < 40U; ++i) {
      feed_string(&protocol, "HELLO?\n");
      protocol.process();
    }
    assert(sink.count == 40U);
  }

  {
    FakeScheduler scheduler;
    FakeEncoder encoder;
    FakeParams params;
    FakeSafety safety;
    OutputSink sink;
    auto protocol = build_protocol(&scheduler, &encoder, &params, &safety, &sink);

    feed_string(&protocol, "SC");
    protocol.process();
    feed_string(&protocol, "HED:1");
    protocol.process();
    feed_string(&protocol, ":22\n");
    protocol.process();
    assert(sink.lines == "OK\n");
    assert(scheduler.last_position == 22);
  }

  {
    FakeScheduler scheduler;
    FakeEncoder encoder;
    FakeParams params;
    FakeSafety safety;
    OutputSink sink;
    auto protocol = build_protocol(&scheduler, &encoder, &params, &safety, &sink);

    feed_string(&protocol, "SCHED:0:1\nSCHED:1:2\nSCHED:2:3\n");
    protocol.process();
    assert(sink.lines == "OK\nOK\nERR\n");
    assert(safety.safe_active);
    assert(safety.enter_safe_calls == 1U);
  }

  {
    FakeScheduler scheduler;
    FakeEncoder encoder;
    FakeParams params;
    FakeSafety safety;
    OutputSink sink;
    auto protocol = build_protocol(&scheduler, &encoder, &params, &safety, &sink);

    feed_string(&protocol, "DOES_NOT_EXIST\n");
    protocol.process();
    assert(sink.lines == "ERR\n");
  }

  {
    FakeScheduler scheduler;
    FakeEncoder encoder;
    FakeParams params;
    FakeSafety safety;
    OutputSink sink;
    auto protocol = build_protocol(&scheduler, &encoder, &params, &safety, &sink);

    feed_string(&protocol, "HELLO?\n");
    protocol.process();
    assert(sink.lines == "HELLO:CVSORTER:1\n");
  }

  {
    FakeScheduler scheduler;
    FakeEncoder encoder;
    FakeParams params;
    FakeSafety safety;
    OutputSink sink;
    auto protocol = build_protocol(&scheduler, &encoder, &params, &safety, &sink);

    feed_string(&protocol, "SCHED:4:10\nPARAM:speed_mm_s:999\nPARAM:bad:1\n");
    protocol.process();
    assert(sink.lines == "ERR\nERR\nERR\n");
  }

  {
    FakeScheduler scheduler;
    scheduler.capacity = 100U;
    FakeEncoder encoder;
    FakeParams params;
    FakeSafety safety;
    OutputSink sink;
    auto protocol = build_protocol(&scheduler, &encoder, &params, &safety, &sink);

    feed_string(&protocol, "HELLO?\nQUEUE?\nPOS?\nMODE:ENCODER\nZERO\nPARAM:speed_mm_s:88\nPARAMS?\n");
    protocol.process();
    assert(sink.count == 7U);
    assert(safety.enter_safe_calls == 0U);
  }

  return 0;
}
