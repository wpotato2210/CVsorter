:::writing{variant=“standard” id=“47261”}

testing_strategy.md

Purpose

Define layered test coverage that verifies correctness of frame processing, queue behavior, mode transitions, scheduler projection, retry semantics, and MCU command emission under deterministic and stressed bench scenarios.

The strategy ensures regression protection across the full runtime pipeline and guarantees deterministic validation of protocol, scheduler, and queue invariants.

⸻

Inputs / Outputs

Inputs
	•	Contracts and protocol artifacts (contracts/*.json, protocol/commands.json)
	•	Runtime modules in:
	•	preprocess
	•	deploy
	•	eval
	•	scheduler
	•	serial_interface
	•	Bench runtime configurations
	•	Synthetic frame streams

Outputs
	•	Pass/fail evidence for:
	•	CV pipeline correctness
	•	protocol conformance
	•	queue/state invariants
	•	Regression protection for:
	•	scheduler projection SCHED:<lane>:<position_mm>
	•	SAFE mode behavior
	•	retry semantics
	•	malformed frame handling

⸻

Terminology Alignment (Protocol + Architecture)

Assertions and fixtures must use protocol-native command and state labels.

All failure assertions must verify canonical NACK error codes defined in protocol.md.

Layered test suites must map directly to the architecture pipeline:

preprocess/calibration → deploy/eval → scheduler → transport


⸻

Test Execution Layers

unit

Validates deterministic behavior of individual modules.

Scope:
	•	preprocess transforms
	•	evaluation logic
	•	scheduler projection math
	•	protocol parsing
	•	queue logic
	•	retry logic

Characteristics:
	•	no external IO
	•	deterministic inputs
	•	no concurrency

⸻

integration

Validates interactions between runtime modules.

Scope:
	•	preprocess → eval
	•	eval → scheduler
	•	scheduler → serial interface
	•	queue state propagation
	•	protocol encoding/decoding

Characteristics:
	•	module boundaries exercised
	•	MCU transport mocked
	•	scheduler/queue interactions verified

⸻

bench_e2e

End-to-end validation using bench runtime configuration.

Scope:
	•	full runtime pipeline
	•	MCU command emission
	•	scheduler projection correctness
	•	SAFE/AUTO/MANUAL mode enforcement
	•	retry behavior with simulated failures

Characteristics:
	•	deterministic synthetic frame streams
	•	real protocol frame encoding
	•	runtime configuration parity

⸻

Runtime Mode Test Matrix

Modes under test:
	•	AUTO
	•	MANUAL
	•	SAFE

Queue depth scenarios:
	•	empty
	•	partial
	•	full

All mode transitions must be validated across these queue states.

⸻

Runtime Mode Transition Tests

The following transitions must be validated.

From	To	Expected Behavior
SAFE	AUTO	rejected
SAFE	MANUAL	allowed
AUTO	SAFE	queue cleared
MANUAL	SAFE	queue cleared

Assertions must verify:
	•	resulting runtime state
	•	emitted protocol commands
	•	queue depth effects
	•	scheduler cancellation behavior

⸻

Queue Invariants

Tests must verify the following invariants:
	•	queue never exceeds maximum depth
	•	queue ordering is FIFO
	•	RESET_QUEUE clears the queue atomically
	•	scheduler never consumes from an empty queue
	•	mode transitions that require queue clearing enforce it

⸻

Retry and Queue Interaction

Retries must not re-enter the scheduler queue.

Retry state is owned by the transport layer and applies only to the currently in-flight command.

Behavior rules:
	•	scheduler emits a command once
	•	transport layer manages retries for that command
	•	retries do not modify scheduler queue depth
	•	retries do not alter scheduler ordering
	•	RESET_QUEUE cancels any in-flight command and its retries

This prevents queue overflow and ordering corruption during retry storms.

⸻

Retry Eligibility Rules

Retries must only occur for transport-level failures.

Retryable conditions
	•	no response received within timeout
	•	corrupted response frame
	•	serial transport error

Non-retryable conditions
	•	protocol NACK responses indicating invalid commands
	•	argument validation failures
	•	illegal state transitions
	•	out-of-range values

When a non-retryable NACK is received:
	•	retries must stop immediately
	•	the error must be surfaced to the caller
	•	scheduler queue state must remain unchanged

⸻

Protocol Negative Tests

Tests must verify canonical NACK behavior for:
	•	malformed frame structure
	•	invalid command arguments
	•	out-of-range numeric values
	•	unknown command identifiers

Assertions must confirm:
	•	correct NACK code
	•	no scheduler side effects
	•	queue state unchanged

⸻

Retry Behavior Verification

Retry tests must verify:
	•	retry count
	•	retry interval (100 ms)
	•	maximum retry attempts (3)
	•	retry termination behavior

Retry exhaustion must produce a deterministic failure state.

⸻

Determinism Requirements

Tests must not depend on wall-clock timing.

Allowed mechanisms:
	•	simulated clocks
	•	deterministic scheduler ticks
	•	virtual time advancement

Real-time sleep calls must not be used in unit or integration tests.

⸻

Deterministic Scheduler Execution

Scheduler tests must run under deterministic execution ordering.

Allowed mechanisms:
	•	single-threaded scheduler mode
	•	controlled worker pools
	•	deterministic task execution

Concurrency stress tests must be separated from deterministic correctness tests.

⸻

Stress Test Scenarios

Bench stress tests should simulate:
	•	burst frame streams
	•	concurrent command bursts
	•	retry storms
	•	queue saturation

Assertions must verify:
	•	no deadlock
	•	scheduler ordering preserved
	•	BUSY state publication correct
	•	queue depth invariants maintained

⸻

Test Coverage Matrix

The following matrix maps runtime modules to the invariants they must enforce.

Module	Invariants	Unit	Integration	Bench E2E
preprocess	deterministic frame transforms	✓	✓	✓
deploy / eval	decision payload correctness	✓	✓	✓
scheduler	canonical projection SCHED:<lane>:<position_mm>	✓	✓	✓
queue	bounded depth, atomic reset, FIFO ordering	✓	✓	✓
serial_interface	correct wire encoding and ACK/NACK parsing	✓	✓	✓
protocol parser	command validation and bounds checking	✓	✓	✓
runtime controller	SAFE/AUTO/MANUAL transition rules	✓	✓	✓
retry logic	timeout and backoff semantics	✓	✓	✓


⸻

Cross-Layer Invariant Enforcement

The following invariants must be validated across multiple test layers.

Invariant	Unit	Integration	Bench
queue never exceeds max depth	✓	✓	✓
RESET_QUEUE clears queue atomically	✓	✓	✓
SAFE mode rejects AUTO transition	✓	✓	✓
scheduler emits canonical projection	✓	✓	✓
malformed frames produce canonical NACK	✓	✓	✓
retry policy respects timeout/backoff	✓	✓	✓


⸻

Dependencies
	•	tests/ suite and fixtures
	•	protocol.md ACK/NACK behavior
	•	architecture.md pipeline ordering and module boundaries
	•	threading_model.md concurrency invariants
	•	constraints.md numeric bounds and transition rules
	•	error_model.md recovery behavior
	•	security_model.md malformed/flood/throttle policies
	•	deployment.md staging/production parity testing

⸻

Performance and Concurrency Notes

Insufficient stress testing can hide:
	•	queue contention
	•	scheduler ordering violations
	•	BUSY publication race conditions
	•	retry storms under burst traffic

Bench traffic patterns must approximate worst-case concurrent frame and command load.

⸻

Open Questions (Requires Input)
	•	minimum coverage targets per module area
	•	whether stress benches must simulate maximum load
	•	whether long-running soak tests are required for release gating
	•	which execution model assumptions (single-threaded vs concurrent producers) must be release blockers

⸻

Missing or Future Test Areas

The following areas are not yet defined and should be addressed in future revisions:
	•	hardware-in-the-loop MCU validation
	•	servo timing verification
	•	real transport latency tolerance
	•	long-duration reliability soak tests
:::