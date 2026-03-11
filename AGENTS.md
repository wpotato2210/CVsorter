# AGENTS.md

Repository: CVsorter  
Purpose: Deterministic computer-vision optical sorting system.

This document defines rules for AI coding agents (Codex, Cursor, Copilot, etc.) operating in this repository.  
Agents must treat these rules as hard constraints.

---

# 1. System Philosophy

CVsorter is a deterministic real-time vision pipeline.

Core properties:

- deterministic processing
- explicit protocol contracts
- stable module boundaries
- real-time reject timing reliability

Agents must preserve these properties at all times.

---

# 2. Frozen Contracts (CRITICAL)

The following files define system architecture and protocol contracts.

Agents MUST NOT modify these files.

protocol.md  
openspec/*  
architecture/*  
bench_spec.md  

These documents define:

- system timing
- message protocol
- module interfaces
- reject timing guarantees

If a requested task requires modifying any of these files:

STOP immediately and report the exact conflict instead of implementing a workaround.

The conflict report must include:

1. the conflicting file path(s),
2. the required contract change summary,
3. impacted command(s)/timing guarantees.

Agents must never silently alter system contracts.

---

# 3. Allowed Modification Areas

Agents may modify or generate code only in these locations:

src/*  
firmware/*  
bench/*  
tests/*  
scripts/*  
tools/*  

Agents must not create new top-level directories without approval.

---

# 4. Determinism Requirements

All implementations must maintain deterministic execution.

Required:

- no uncontrolled randomness
- seeded randomness only when required
- deterministic ordering of operations
- deterministic naming
- deterministic output for identical inputs

Forbidden:

- non-seeded random operations
- time-dependent behavior
- hidden state mutations
- nondeterministic threading behavior

---

# 5. Computer Vision Pipeline Rules

When generating CV modules agents must explicitly declare:

- input tensor shape
- output tensor shape
- color format (RGB or BGR)
- normalization range
- device placement (CPU/GPU)

Example:

input:  (H, W, 3) BGR uint8  
output: (N,) class probabilities  
norm:   [0,1]  
device: cpu  

Implicit assumptions are not allowed.

---

# 6. Module Interface Contracts

All modules must define:

inputs  
outputs  
side effects  
dependencies  
update rate  

Example structure:

Module: classifier

Inputs:
- frame: (H,W,3) BGR

Outputs:
- class_id
- confidence

Update Rate:
per frame

Agents must maintain compatibility with existing module contracts.

---

# 7. Serial / Hardware Interface Safety

Hardware interfaces must remain deterministic.

Required:

- explicit message format
- checksum when protocol requires
- bounded latency
- watchdog handling

Agents must not introduce:

- blocking I/O inside real-time loops
- uncontrolled retries
- hidden buffering

---

# 8. Code Generation Rules

All generated code must include:

- full type hints
- minimal boilerplate
- explicit I/O contracts
- deterministic naming
- clear module boundaries

Avoid:

- unnecessary abstractions
- heavy frameworks
- hidden dependencies

---

# 9. Bench / Simulation Integrity

Bench tools simulate sorter timing behavior.

Agents must ensure:

- reject timing windows remain measurable
- latency metrics remain reproducible
- simulation inputs remain deterministic

Bench tools must not modify protocol definitions.

---

# 10. Testing Requirements

When modifying or adding code:

Agents must update or generate tests in:

tests/*  
bench/*  

Primary commands to run:

- firmware unit tests: `run_tests.bat`
- host test suite: `pytest tests/`
- integration timing/trace checks: `pytest bench/`
- coverage artifact (when coverage is required): `pytest --cov=src/coloursorter --cov-report=xml`

Required pass condition:

- all executed commands must be green
- zero skipped tests for any critical test group
- deterministic behavior, protocol compliance, and latency boundaries must all be validated

Artifact expectations:

- test logs for each executed command must be captured in terminal output or attached logs
- `coverage.xml` must be produced when coverage is required
- any integration trace output required by bench tests must be preserved as run artifacts/logs

Fallback behavior for unavailable dependencies:

- report each blocked command explicitly
- include the exact blocker reason (missing dependency/tool, platform limitation, or environment failure)
- provide partial results from all commands that did run, including any produced logs/artifacts

---

# 11. When Uncertain

Agents must prefer:

1. protocol compliance
2. determinism
3. explicit contracts

Agents must request clarification instead of modifying system contracts.

---

# 12. Agent Behavior Guidelines

Agents should:

- modify the smallest possible scope
- avoid large refactors unless requested
- avoid renaming public interfaces
- avoid modifying protocol definitions
- preserve existing architecture

---

# 13. Security and Stability

Agents must not introduce:

- network dependencies without approval
- telemetry
- external services
- hidden downloads
- runtime package installs

The system must remain fully reproducible offline.

---

# 14. Documentation Updates

Documentation may be updated only in:

docs/*  
README.md  

Agents must not rewrite system architecture documents.

---

# 15. Summary

Priority order for all agent actions:

1. preserve frozen contracts  
2. maintain determinism  
3. preserve module interfaces  
4. minimize scope of changes  
5. maintain test coverage  

If any task conflicts with these rules:

STOP and request human approval.

## Testing
- Run tests: `run_tests.bat`
- Coverage: `pytest --cov=src/coloursorter` produces `coverage.xml`
- Test files must be in `tests/` folder and named `test_*.py`
- Do not modify existing source files; add new tests only
