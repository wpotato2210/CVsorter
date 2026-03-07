:::writing{variant=“standard” id=“90341”}

Controller Architecture

Overview

The controller manages runtime playback modes and coordinates transitions between live execution and replay playback.
It acts as the central authority for:
	•	runtime mode selection
	•	replay activation
	•	event emission for downstream components
	•	UI timer consistency

The controller enforces strict transition rules to prevent inconsistent runtime state or unintended side-effects.

⸻

Controller Responsibilities

The controller is responsible for:
	1.	Maintaining the runtime state machine
	2.	Validating requested state transitions
	3.	Emitting transition events
	4.	Preventing illegal transitions
	5.	Preserving runtime UI consistency

The controller must not allow side effects to occur when a transition is invalid.

⸻

Controller State Machine

States

State	Description
LIVE	System is running in real-time mode
REPLAY	System is playing back recorded data


⸻

Valid Transitions

LIVE → REPLAY

Trigger:
	•	replay request

Behavior:
	•	controller state changes from LIVE to REPLAY
	•	event start_replay is emitted exactly once
	•	event start_live must not be emitted
	•	runtime UI timer remains consistent with replay timeline

This transition activates replay playback while ensuring the runtime UI reflects the replay state.

⸻

Illegal Transitions

REPLAY → LIVE (direct request)

Direct transition from replay to live is not allowed.

Handling rules:
	1.	The request is ignored
	2.	Controller state remains REPLAY
	3.	start_live must not be emitted
	4.	No transition side effects occur
	5.	Runtime UI timer remains unchanged

Illegal transition handling prevents unintended UI resets or replay interruption.

⸻

Event Emission Guarantees

The controller enforces strict transition-event semantics.

Event	Guarantee
start_replay	emitted exactly once when entering replay
start_live	never emitted during replay transitions
any transition event	never emitted for illegal transitions

These guarantees prevent downstream components from reacting to invalid state changes.

⸻

Runtime UI Timer Behavior

The runtime UI timer reflects the current execution timeline.

Behavior rules:
	•	entering replay mode aligns the timer with replay timeline
	•	replay playback controls timer progression
	•	illegal transitions must not modify the timer
	•	timer state must remain stable when a transition request is rejected

This prevents UI inconsistencies during replay operations.

⸻

Transition Table

Current State	Requested Transition	Result	Events Emitted
LIVE	REPLAY	Allowed	start_replay (once)
REPLAY	LIVE	Illegal	none


⸻

Illegal Transition Policy

When an invalid transition is requested:
	1.	The request is ignored
	2.	The controller state remains unchanged
	3.	No transition events are emitted
	4.	Runtime UI state must remain unchanged

Illegal transitions must never produce side effects.

⸻

Testing Requirements

Controller tests must verify three aspects of behavior:

1. Final Controller State

The controller must end in the expected state after a transition request.

2. Event Emission

Tests must verify which events were emitted and how many times.

Example expectations:
	•	start_replay emitted exactly once
	•	start_live never emitted during replay transitions

3. Runtime Side Effects

Tests must verify that runtime state remains consistent, including:
	•	UI timer stability
	•	replay playback state
	•	absence of side effects for illegal transitions

State-only assertions are insufficient for controller transition testing.

⸻

Example Test Coverage

The following scenario is explicitly validated by tests:

Illegal replay → live transition

Expected behavior:
	•	controller remains in REPLAY
	•	start_live is not emitted
	•	start_replay remains emitted only once
	•	runtime UI timer remains unchanged

This ensures replay playback cannot be interrupted by invalid transition requests.

⸻

Design Principles

The controller follows these principles:

Deterministic transitions

Transitions must have predictable outcomes.

Side-effect isolation

Events must only occur when transitions are valid.

Strict illegal-transition handling

Invalid requests must not affect runtime behavior.

UI stability

Runtime UI state must remain consistent across rejected transitions.

⸻

Summary

The controller enforces a strict state-machine model to guarantee safe transitions between live and replay modes.

Key guarantees:
	•	replay activation emits start_replay exactly once
	•	replay transitions never emit start_live
	•	illegal transitions are ignored
	•	runtime UI timers remain stable
	•	transition side effects only occur for valid transitions
:::