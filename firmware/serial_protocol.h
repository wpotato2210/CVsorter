#ifndef CVSORTER_FIRMWARE_SERIAL_PROTOCOL_H_
#define CVSORTER_FIRMWARE_SERIAL_PROTOCOL_H_

#include <cstddef>
#include <cstdint>

namespace cvsorter {

constexpr std::size_t kSerialRingBufferSize = 256U;
constexpr std::size_t kLineBufferSize = 128U;
constexpr std::size_t kParamSnapshotCapacity = 16U;
constexpr const char* kProtocolHelloResponse = "HELLO:CVSORTER:1";

static_assert(kSerialRingBufferSize >= 256U, "Serial ring buffer must be at least 256 bytes.");

enum class ProtocolMode : std::uint8_t {
  kEncoder = 0U,
  kTime = 1U,
};

struct ParamSnapshot {
  const char* name;
  std::int32_t value;
};

struct SchedulerApi {
  bool (*enqueue)(std::uint8_t lane, std::int32_t position_mm, void* context);
  std::uint16_t (*queue_size)(void* context);
  void* context;
};

struct EncoderApi {
  std::int32_t (*position)(void* context);
  void (*zero)(void* context);
  void* context;
};

struct ParamsApi {
  bool (*set_mode)(ProtocolMode mode, void* context);
  bool (*set_param)(const char* name, std::int32_t value, void* context);
  bool (*get_param)(const char* name, std::int32_t* out_value, void* context);
  std::size_t (*list_params)(ParamSnapshot* out_params, std::size_t max_params, void* context);
  void* context;
};

struct SafetyApi {
  bool (*is_safe_active)(void* context);
  void (*enter_safe)(void* context);
  void (*clear_safe)(void* context);
  void* context;
};

using ResponseWriter = void (*)(const char* response, void* context);

template <std::size_t QueueCapacity>
class QueueCapacityGuard {
 public:
  static_assert(QueueCapacity > 0U, "QUEUE_CAPACITY must be greater than zero.");
};

class SerialProtocol {
 public:
  static constexpr std::size_t kQueueCapacity = 512U;
  using QueueCapacityStaticCheck = QueueCapacityGuard<kQueueCapacity>;

  SerialProtocol(std::uint8_t max_lanes,
                 SchedulerApi scheduler,
                 EncoderApi encoder,
                 ParamsApi params,
                 SafetyApi safety,
                 ResponseWriter writer,
                 void* writer_context);

  bool ingest_byte(std::uint8_t byte_value);
  std::size_t ingest_bytes(const std::uint8_t* bytes, std::size_t length);
  std::size_t process();

 private:
  bool pop_byte(std::uint8_t* out_byte);
  void dispatch_line(const char* line);
  void write_response(const char* response) const;

  std::uint8_t max_lanes_;
  SchedulerApi scheduler_;
  EncoderApi encoder_;
  ParamsApi params_;
  SafetyApi safety_;
  ResponseWriter writer_;
  void* writer_context_;

  std::uint8_t ring_buffer_[kSerialRingBufferSize];
  std::size_t ring_head_;
  std::size_t ring_tail_;
  std::size_t ring_count_;

  char line_buffer_[kLineBufferSize];
  std::size_t line_size_;
  bool dropping_long_line_;
};

}  // namespace cvsorter

#endif  // CVSORTER_FIRMWARE_SERIAL_PROTOCOL_H_
