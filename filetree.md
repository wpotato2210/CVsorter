:::writing{variant=“standard” id=“90562”}

repository_map.md

Scope

Reverse-engineered repository map intended for:
	•	onboarding developers
	•	ChatGPT / AI task scoping
	•	rapid navigation of runtime components
	•	debugging entry guidance

This document highlights repository structure, runtime pipeline flow, module responsibilities, and common debugging locations.

⸻

Top-Level Repository Structure

ColourSorter/
├── src/coloursorter/
│   ├── bench/                # Bench runner, frame sources, transport adapters, CLI
│   ├── calibration/          # Pixel-to-mm mapping and geometric calibration
│   ├── config/               # Runtime configuration parsing and validation
│   ├── deploy/               # Pipeline orchestration layer
│   ├── eval/                 # Decision logic and reject rules
│   ├── model/                # Core typed contracts and shared data models
│   ├── preprocess/           # Frame preprocessing and lane segmentation
│   ├── protocol/             # Protocol constants, host policy, NACK mapping
│   ├── scheduler/            # Scheduled command output generation
│   ├── serial_interface/     # Wire encode/decode and packet parsing
│   └── train/                # Training artifacts / placeholders
│
├── gui/bench_app/            # Qt bench GUI controller and window app
├── tests/                    # Unit, integration, and compliance tests
├── contracts/                # JSON schemas (frame/schedule/MCU response)
├── protocol/                 # Protocol command contract JSON
├── configs/                  # Runtime, bench, geometry, calibration configs
├── docs/openspec/v3/         # Versioned OpenSpec mirrors and compliance docs
├── data/                     # Data manifest
├── tools/                    # Utility scripts (readiness reporting etc.)
│
├── README.md
├── architecture.md
├── openspec.md
└── pyproject.toml


⸻

Runtime Pipeline Overview

The runtime pipeline processes incoming frames and produces MCU commands.

Execution flow:

frame source
    ↓
preprocess
    ↓
eval
    ↓
scheduler
    ↓
serial_interface
    ↓
MCU

Pipeline orchestration occurs inside the deploy module.

⸻

Source Module Responsibilities

bench

Bench execution environment.

Responsibilities:
	•	frame source adapters
	•	transport simulation
	•	command runner
	•	CLI interface

Primary files:

src/coloursorter/bench/runner.py
src/coloursorter/bench/cli.py


⸻

calibration

Geometry and coordinate transformation.

Responsibilities:
	•	pixel-to-mm mapping
	•	camera calibration
	•	geometry validation

⸻

config

Runtime configuration system.

Responsibilities:
	•	configuration parsing
	•	schema validation
	•	runtime parameter loading

⸻

deploy

Pipeline orchestration layer.

Responsibilities:
	•	connecting runtime modules
	•	initialization of pipeline components
	•	runtime lifecycle management

⸻

eval

Decision and classification logic.

Responsibilities:
	•	classification rules
	•	reject conditions
	•	routing decisions

⸻

model

Shared data contracts.

Responsibilities:
	•	frame structures
	•	scheduler outputs
	•	typed shared models

⸻

preprocess

Frame preprocessing stage.

Responsibilities:
	•	lane segmentation
	•	preprocessing transforms
	•	frame normalization

⸻

protocol

Host protocol policy.

Responsibilities:
	•	command constants
	•	protocol policy enforcement
	•	canonical NACK mapping

Related files:

protocol/commands.json


⸻

scheduler

Command scheduling logic.

Responsibilities:
	•	projection calculation
	•	scheduling decisions
	•	command output generation

Primary output format:

SCHED:<lane>:<position_mm>


⸻

serial_interface

Transport and wire protocol layer.

Responsibilities:
	•	wire frame encoding
	•	packet decoding
	•	retry behavior
	•	ACK/NACK handling

Primary files:

src/coloursorter/serial_interface/serial_interface.py
src/coloursorter/serial_interface/wire.py


⸻

train

Placeholder for training artifacts and experimentation.

Not part of the runtime pipeline.

⸻

GUI Components

Location:

gui/bench_app/

Responsibilities:
	•	GUI runtime controller
	•	visualization for bench testing
	•	interactive test execution

Primary files:

gui/bench_app/controller.py
gui/bench_app/app.py


⸻

Test Structure

Location:

tests/

Test layers include:
	•	unit tests
	•	integration tests
	•	protocol compliance tests

Primary entry:

tests/test_integration.py

Additional tests target individual modules.

⸻

Contracts and Schemas

Location:

contracts/

Contains JSON schemas for:
	•	frame structures
	•	scheduler output
	•	MCU responses

Used for validation in tests and protocol handling.

⸻

Protocol Contracts

Location:

protocol/

Defines canonical protocol commands and constraints.

Primary file:

protocol/commands.json

Includes:
	•	command identifiers
	•	argument bounds
	•	protocol structure definitions

⸻

Configuration Files

Location:

configs/

Contains runtime configuration sets:
	•	runtime configs
	•	bench configs
	•	geometry configs
	•	calibration configs

⸻

OpenSpec Mirrors

Location:

docs/openspec/v3/

Contains versioned OpenSpec documents used for specification compliance and traceability.

⸻

Tools

Location:

tools/

Contains developer utilities such as:
	•	readiness reporting
	•	validation scripts
	•	diagnostic helpers

⸻

Execution Entry Points

Primary execution entry files.

Purpose	File
Bench execution	src/coloursorter/bench/runner.py
CLI interface	src/coloursorter/bench/cli.py
GUI launch	gui/bench_app/app.py


⸻

Fast Navigation Index

Task	Primary Files
Protocol behavior	src/coloursorter/protocol/*, protocol/commands.json
Wire parsing / serialization	serial_interface/serial_interface.py, serial_interface/wire.py
Scheduler output	scheduler/output.py
Bench execution	bench/runner.py, bench/cli.py
GUI runtime loop	gui/bench_app/controller.py, gui/bench_app/app.py
OpenSpec mirrors	docs/openspec/v3/**
Test entry	tests/test_integration.py


⸻

Common Failure Points

These modules historically produce most runtime issues.

⸻

Frame Preprocessing

Location:

src/coloursorter/preprocess/

Typical issues:
	•	incorrect lane segmentation
	•	frame coordinate drift
	•	calibration mismatch

Symptoms:
	•	objects assigned to wrong lane
	•	incorrect scheduler inputs

⸻

Calibration / Geometry Mapping

Location:

src/coloursorter/calibration/
configs/geometry*

Typical issues:
	•	pixel-to-mm conversion errors
	•	stale calibration parameters

Symptoms:
	•	incorrect position_mm projection

⸻

Decision Logic

Location:

src/coloursorter/eval/

Typical issues:
	•	incorrect rule ordering
	•	threshold misconfiguration

Symptoms:
	•	unexpected classification or rejection

⸻

Scheduler Projection

Location:

src/coloursorter/scheduler/output.py

Typical issues:
	•	incorrect projection math
	•	lane mapping errors

Symptoms:
	•	malformed scheduler output
	•	incorrect command timing

⸻

Protocol Encoding / Decoding

Location:

src/coloursorter/serial_interface/
src/coloursorter/protocol/

Typical issues:
	•	wire framing errors
	•	ACK/NACK misinterpretation

Symptoms:
	•	MCU rejecting commands
	•	protocol desynchronization

⸻

Retry / Transport Handling

Location:

src/coloursorter/serial_interface/

Typical issues:
	•	retry storms
	•	transport timeouts
	•	lost ACK responses

Symptoms:
	•	repeated command transmissions
	•	queue backpressure

⸻

Bench Environment

Location:

src/coloursorter/bench/
gui/bench_app/

Typical issues:
	•	synthetic frame timing mismatch
	•	configuration drift

Symptoms:
	•	inconsistent bench behavior

⸻

Debugging Entry Points

When diagnosing problems, inspect these files first.

Issue Type	First File
frame segmentation	preprocess/*
projection errors	scheduler/output.py
command rejection	protocol/*
wire corruption	serial_interface/wire.py
retry loops	serial_interface/serial_interface.py
bench execution	bench/runner.py


⸻

AI Task Scoping Guidance

When asking AI tools to analyze or modify the repository:
	1.	Provide the specific module directory
	2.	Include relevant protocol contracts or configs
	3.	Identify the pipeline stage involved
	4.	Provide the scheduler output or protocol command

Example prompt:

Analyze scheduler projection logic in:

src/coloursorter/scheduler/output.py

Verify correctness of SCHED:<lane>:<position_mm>
generation based on inputs from eval and calibration modules.


⸻

Key Documentation

Important project documents.

File	Purpose
README.md	project overview
architecture.md	system architecture
openspec.md	specification alignment

These documents define system design constraints and implementation guidelines.
:::