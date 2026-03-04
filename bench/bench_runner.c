#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef BENCH_STANDALONE
typedef struct {
    int32_t ticks;
    int32_t mm_q16;
} motion_cmd_t;

enum { QUEUE_CAP = 16 };
typedef enum { SAFE_REASON_NONE = 0, SAFE_REASON_QUEUE_OVERFLOW = 1, SAFE_REASON_ENCODER_TIMEOUT = 2 } safe_reason_t;

typedef struct {
    motion_cmd_t queue[QUEUE_CAP];
    uint8_t head;
    uint8_t tail;
    uint8_t depth;
    uint32_t last_tick_ms;
    int32_t encoder_ticks;
    uint32_t timeout_ms;
    int32_t next_trigger_at;
    int32_t ticks_per_mm_q16;
    bool safe;
    safe_reason_t safe_reason;
} bench_state_t;

static bench_state_t g = {.timeout_ms = 200};

static void disable_servo_callback(void) {}

void encoder_init(uint32_t now_ms) { g.last_tick_ms = now_ms; g.encoder_ticks = 0; }
void scheduler_init(int32_t ticks_per_mm_q16) { g.ticks_per_mm_q16 = ticks_per_mm_q16; g.next_trigger_at = 0; }
void safety_init(void (*disable_servo_cb)(void)) { (void)disable_servo_cb; g.safe = false; g.safe_reason = SAFE_REASON_NONE; }

void encoder_on_tick_isr(int32_t delta_ticks, uint32_t now_ms) { g.encoder_ticks += delta_ticks; g.last_tick_ms = now_ms; }
int32_t encoder_get_ticks(void) { return g.encoder_ticks; }

bool encoder_has_timed_out(uint32_t now_ms) { return (now_ms - g.last_tick_ms) > g.timeout_ms; }
void safety_report_encoder_timeout(void) { g.safe = true; g.safe_reason = SAFE_REASON_ENCODER_TIMEOUT; disable_servo_callback(); }
void safety_report_queue_overflow(void) { g.safe = true; g.safe_reason = SAFE_REASON_QUEUE_OVERFLOW; disable_servo_callback(); }
void safety_clear(void) { g.safe = false; g.safe_reason = SAFE_REASON_NONE; }

bool queue_push(motion_cmd_t cmd) {
    if (g.depth >= QUEUE_CAP) {
        safety_report_queue_overflow();
        return false;
    }
    g.queue[g.tail] = cmd;
    g.tail = (uint8_t)((g.tail + 1U) % QUEUE_CAP);
    g.depth++;
    return true;
}

bool queue_peek(motion_cmd_t *out) { if (g.depth == 0) return false; *out = g.queue[g.head]; return true; }
void queue_pop(void) { if (g.depth == 0) return; g.head = (uint8_t)((g.head + 1U) % QUEUE_CAP); g.depth--; }
uint8_t queue_depth(void) { return g.depth; }

bool scheduler_should_trigger(const motion_cmd_t *cmd, int32_t encoder_ticks_now) {
    if (g.next_trigger_at == 0) g.next_trigger_at = encoder_ticks_now + cmd->ticks;
    if (encoder_ticks_now >= g.next_trigger_at) {
        g.next_trigger_at = 0;
        return true;
    }
    return false;
}

bool safety_is_safe(void) { return g.safe; }
int safety_reason(void) { return (int)g.safe_reason; }

#else
#include "encoder.h"
#include "queue.h"
#include "safety.h"
#include "scheduler.h"

int32_t encoder_get_ticks(void);
bool safety_is_safe(void);
int safety_reason(void);
#endif

static const char *safe_reason_name(int reason) {
    switch (reason) {
        case 1: return "QUEUE_OVERFLOW";
        case 2: return "ENCODER_TIMEOUT";
        default: return "NONE";
    }
}

static void run_step(uint32_t *now_ms, uint32_t step_ms, int32_t synthetic_ticks, int32_t observed_ticks) {
    motion_cmd_t cmd;

    *now_ms += step_ms;
    if (synthetic_ticks != 0) encoder_on_tick_isr(synthetic_ticks, *now_ms);
    if (observed_ticks != 0) encoder_on_tick_isr(observed_ticks, *now_ms);

    if (queue_peek(&cmd) && scheduler_should_trigger(&cmd, encoder_get_ticks())) queue_pop();
    if (encoder_has_timed_out(*now_ms)) safety_report_encoder_timeout();
}

int main(void) {
    uint32_t now_ms = 0;
    int32_t synthetic_ticks = 0;
    char line[128];

    encoder_init(now_ms);
    scheduler_init(65536);
    safety_init(disable_servo_callback);

    puts("bench_runner ready");
    while (fgets(line, sizeof(line), stdin) != NULL) {
        if (strncmp(line, "STEP ", 5) == 0) {
            run_step(&now_ms, (uint32_t)strtoul(line + 5, NULL, 10), synthetic_ticks, 0);
        } else if (strncmp(line, "SYNTH ", 6) == 0) {
            synthetic_ticks = (int32_t)strtol(line + 6, NULL, 10);
        } else if (strncmp(line, "OBS_TICK ", 9) == 0) {
            run_step(&now_ms, 1, synthetic_ticks, (int32_t)strtol(line + 9, NULL, 10));
        } else if (strncmp(line, "ENQUEUE ", 8) == 0) {
            motion_cmd_t cmd;
            cmd.ticks = (int32_t)strtol(line + 8, NULL, 10);
#ifdef BENCH_STANDALONE
            cmd.mm_q16 = (g.ticks_per_mm_q16 == 0) ? 0 : (cmd.ticks << 16) / g.ticks_per_mm_q16;
#else
            cmd.mm_q16 = 0;
#endif
            (void)queue_push(cmd);
        } else if (strncmp(line, "CLEAR_SAFE", 10) == 0) {
            safety_clear();
        } else if (strncmp(line, "STATUS", 6) == 0) {
            printf("state=%s reason=%s queue_depth=%u now_ms=%u\n",
                   safety_is_safe() ? "SAFE" : "RUN",
                   safe_reason_name(safety_reason()),
                   (unsigned)queue_depth(),
                   (unsigned)now_ms);
        } else if (strncmp(line, "QUIT", 4) == 0) {
            break;
        }
    }

    return 0;
}
