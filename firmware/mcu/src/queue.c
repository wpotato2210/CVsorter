#include "queue.h"

#include <stddef.h>

static event_t s_heap[QUEUE_CAPACITY];
static uint16_t s_size = 0U;

static void heap_swap(uint16_t a, uint16_t b) {
  event_t tmp = s_heap[a];
  s_heap[a] = s_heap[b];
  s_heap[b] = tmp;
}

bool queue_push(event_t e) {
  if (s_size >= QUEUE_CAPACITY) {
    return false;
  }

  uint16_t idx = s_size;
  s_heap[idx] = e;
  s_size += 1U;

  while (idx > 0U) {
    uint16_t parent = (uint16_t)((idx - 1U) / 2U);
    if (s_heap[parent].trigger_tick <= s_heap[idx].trigger_tick) {
      break;
    }
    heap_swap(parent, idx);
    idx = parent;
  }

  return true;
}

bool queue_pop(event_t *out) {
  if (out == NULL || s_size == 0U) {
    return false;
  }

  *out = s_heap[0];
  s_size -= 1U;
  if (s_size == 0U) {
    return true;
  }

  s_heap[0] = s_heap[s_size];

  uint16_t idx = 0U;
  for (;;) {
    uint16_t left = (uint16_t)(2U * idx + 1U);
    uint16_t right = (uint16_t)(left + 1U);
    uint16_t smallest = idx;

    if (left < s_size && s_heap[left].trigger_tick < s_heap[smallest].trigger_tick) {
      smallest = left;
    }
    if (right < s_size && s_heap[right].trigger_tick < s_heap[smallest].trigger_tick) {
      smallest = right;
    }
    if (smallest == idx) {
      break;
    }
    heap_swap(idx, smallest);
    idx = smallest;
  }

  return true;
}

bool queue_peek(event_t *out) {
  if (out == NULL || s_size == 0U) {
    return false;
  }
  *out = s_heap[0];
  return true;
}

uint16_t queue_size(void) {
  return s_size;
}

void queue_clear(void) {
  s_size = 0U;
}
