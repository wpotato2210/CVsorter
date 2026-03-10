#include "serial_protocol.h"

#include <cctype>
#include <cstdio>
#include <cstring>

namespace cvsorter {
namespace {

bool parse_nonnegative_int(const char* text, std::int32_t* out_value) {
  if (text == nullptr || out_value == nullptr || *text == '\0') {
    return false;
  }

  std::int64_t value = 0;
  for (const char* cursor = text; *cursor != '\0'; ++cursor) {
    if (!std::isdigit(static_cast<unsigned char>(*cursor))) {
      return false;
    }
    value = (value * 10) + static_cast<std::int64_t>(*cursor - '0');
    if (value > static_cast<std::int64_t>(INT32_MAX)) {
      return false;
    }
  }

  *out_value = static_cast<std::int32_t>(value);
  return true;
}

void split_tokens(char* text, char separator, char** out_tokens, std::size_t* in_out_count) {
  if (text == nullptr || out_tokens == nullptr || in_out_count == nullptr || *in_out_count == 0U) {
    return;
  }

  std::size_t token_count = 0U;
  char* start = text;
  for (char* cursor = text;; ++cursor) {
    if (*cursor == separator || *cursor == '\0') {
      if (token_count < *in_out_count) {
        out_tokens[token_count] = start;
        ++token_count;
      }
      if (*cursor == '\0') {
        break;
      }
      *cursor = '\0';
      start = cursor + 1;
    }
  }
  *in_out_count = token_count;
}

}  // namespace

SerialProtocol::SerialProtocol(std::uint8_t max_lanes,
                               SchedulerApi scheduler,
                               EncoderApi encoder,
                               ParamsApi params,
                               SafetyApi safety,
                               ResponseWriter writer,
                               void* writer_context)
    : max_lanes_(max_lanes),
      scheduler_(scheduler),
      encoder_(encoder),
      params_(params),
      safety_(safety),
      writer_(writer),
      writer_context_(writer_context),
      ring_buffer_{0U},
      ring_head_(0U),
      ring_tail_(0U),
      ring_count_(0U),
      line_buffer_{0},
      line_size_(0U),
      dropping_long_line_(false) {}

bool SerialProtocol::ingest_byte(std::uint8_t byte_value) {
  if (ring_count_ >= kSerialRingBufferSize) {
    if (safety_.enter_safe != nullptr) {
      safety_.enter_safe(safety_.context);
    }
    return false;
  }

  ring_buffer_[ring_head_] = byte_value;
  ring_head_ = (ring_head_ + 1U) % kSerialRingBufferSize;
  ++ring_count_;
  return true;
}

std::size_t SerialProtocol::ingest_bytes(const std::uint8_t* bytes, std::size_t length) {
  if (bytes == nullptr) {
    return 0U;
  }

  std::size_t accepted = 0U;
  for (std::size_t i = 0U; i < length; ++i) {
    if (!ingest_byte(bytes[i])) {
      break;
    }
    ++accepted;
  }
  return accepted;
}

bool SerialProtocol::pop_byte(std::uint8_t* out_byte) {
  if (out_byte == nullptr || ring_count_ == 0U) {
    return false;
  }

  *out_byte = ring_buffer_[ring_tail_];
  ring_tail_ = (ring_tail_ + 1U) % kSerialRingBufferSize;
  --ring_count_;
  return true;
}

void SerialProtocol::write_response(const char* response) const {
  if (writer_ != nullptr && response != nullptr) {
    writer_(response, writer_context_);
  }
}

void SerialProtocol::dispatch_line(const char* line) {
  if (line == nullptr || *line == '\0') {
    write_response("ERR");
    return;
  }

  if (std::strcmp(line, "HELLO?") == 0) {
    write_response(kProtocolHelloResponse);
    return;
  }
  if (std::strcmp(line, "POS?") == 0) {
    if (encoder_.position == nullptr) {
      write_response("ERR");
      return;
    }
    char response[48];
    const std::int32_t value = encoder_.position(encoder_.context);
    std::snprintf(response, sizeof(response), "POS:%ld", static_cast<long>(value));
    write_response(response);
    return;
  }
  if (std::strcmp(line, "QUEUE?") == 0) {
    if (scheduler_.queue_size == nullptr) {
      write_response("ERR");
      return;
    }
    char response[48];
    const unsigned int value = static_cast<unsigned int>(scheduler_.queue_size(scheduler_.context));
    std::snprintf(response, sizeof(response), "QUEUE:%u", value);
    write_response(response);
    return;
  }
  if (std::strcmp(line, "PARAMS?") == 0) {
    if (params_.list_params == nullptr) {
      write_response("ERR");
      return;
    }
    ParamSnapshot snapshot[kParamSnapshotCapacity];
    const std::size_t count = params_.list_params(snapshot, kParamSnapshotCapacity, params_.context);
    char response[256];
    std::size_t cursor = 0U;
    if (count == 0U) {
      std::snprintf(response, sizeof(response), "PARAM:");
      write_response(response);
      return;
    }

    for (std::size_t i = 0U; i < count; ++i) {
      const int written = std::snprintf(response + cursor,
                                        sizeof(response) - cursor,
                                        "%s%s:%ld",
                                        i == 0U ? "PARAM:" : ";",
                                        snapshot[i].name,
                                        static_cast<long>(snapshot[i].value));
      if (written <= 0) {
        write_response("ERR");
        return;
      }
      const std::size_t width = static_cast<std::size_t>(written);
      if (width >= (sizeof(response) - cursor)) {
        write_response("ERR");
        return;
      }
      cursor += width;
    }
    write_response(response);
    return;
  }
  if (std::strcmp(line, "CLEAR_SAFE") == 0) {
    if (safety_.clear_safe != nullptr) {
      safety_.clear_safe(safety_.context);
    }
    write_response("OK");
    return;
  }
  if (std::strcmp(line, "ZERO") == 0) {
    if (encoder_.zero == nullptr) {
      write_response("ERR");
      return;
    }
    encoder_.zero(encoder_.context);
    write_response("OK");
    return;
  }

  char command[kLineBufferSize];
  std::strncpy(command, line, sizeof(command) - 1U);
  command[sizeof(command) - 1U] = '\0';

  char* tokens[4] = {nullptr, nullptr, nullptr, nullptr};
  std::size_t token_count = 4U;
  split_tokens(command, ':', tokens, &token_count);

  if (token_count == 2U && std::strcmp(tokens[0], "MODE") == 0) {
    if (params_.set_mode == nullptr) {
      write_response("ERR");
      return;
    }
    const bool is_encoder = std::strcmp(tokens[1], "ENCODER") == 0;
    const bool is_time = std::strcmp(tokens[1], "TIME") == 0;
    if (!is_encoder && !is_time) {
      write_response("ERR");
      return;
    }
    const ProtocolMode mode = is_encoder ? ProtocolMode::kEncoder : ProtocolMode::kTime;
    write_response(params_.set_mode(mode, params_.context) ? "OK" : "ERR");
    return;
  }

  if (token_count == 3U && std::strcmp(tokens[0], "SCHED") == 0) {
    if (scheduler_.enqueue == nullptr || safety_.is_safe_active == nullptr) {
      write_response("ERR");
      return;
    }

    std::int32_t lane = -1;
    std::int32_t position_mm = -1;
    if (!parse_nonnegative_int(tokens[1], &lane) || !parse_nonnegative_int(tokens[2], &position_mm)) {
      write_response("ERR");
      return;
    }
    if (lane < 0 || lane >= static_cast<std::int32_t>(max_lanes_) || position_mm < 0) {
      write_response("ERR");
      return;
    }
    if (safety_.is_safe_active(safety_.context)) {
      write_response("ERR");
      return;
    }

    const bool queued = scheduler_.enqueue(static_cast<std::uint8_t>(lane), position_mm, scheduler_.context);
    if (!queued) {
      if (safety_.enter_safe != nullptr) {
        safety_.enter_safe(safety_.context);
      }
      write_response("ERR");
      return;
    }
    write_response("OK");
    return;
  }

  if (token_count == 3U && std::strcmp(tokens[0], "PARAM") == 0) {
    if (params_.get_param == nullptr || params_.set_param == nullptr) {
      write_response("ERR");
      return;
    }

    std::int32_t ignored_value = 0;
    if (!params_.get_param(tokens[1], &ignored_value, params_.context)) {
      write_response("ERR");
      return;
    }

    std::int32_t param_value = 0;
    if (!parse_nonnegative_int(tokens[2], &param_value)) {
      write_response("ERR");
      return;
    }

    write_response(params_.set_param(tokens[1], param_value, params_.context) ? "OK" : "ERR");
    return;
  }

  write_response("ERR");
}

std::size_t SerialProtocol::process() {
  std::size_t command_count = 0U;
  std::uint8_t byte_value = 0U;
  while (pop_byte(&byte_value)) {
    if (dropping_long_line_) {
      if (byte_value == '\n') {
        dropping_long_line_ = false;
        line_size_ = 0U;
        write_response("ERR");
        ++command_count;
      }
      continue;
    }

    if (byte_value == '\r') {
      continue;
    }

    if (byte_value == '\n') {
      line_buffer_[line_size_] = '\0';
      dispatch_line(line_buffer_);
      line_size_ = 0U;
      ++command_count;
      continue;
    }

    if (line_size_ >= (kLineBufferSize - 1U)) {
      line_size_ = 0U;
      dropping_long_line_ = true;
      continue;
    }

    line_buffer_[line_size_] = static_cast<char>(byte_value);
    ++line_size_;
  }

  return command_count;
}

}  // namespace cvsorter
