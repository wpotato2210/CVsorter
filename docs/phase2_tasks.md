# Phase 2 Task Plan (Deterministic CV Pipeline)

## Scope
Phase 2 focuses on deterministic hardening and readiness across:
- `preprocess`
- `model`
- `train`
- `eval`
- `deploy`

## Pipeline I/O + Dependencies
```mermaid
flowchart LR
    A[Input Frame\nI/O: (H,W,3) BGR uint8] --> B[preprocess]
    B --> C[model]
    C --> D[eval]
    D --> E[deploy]
    T[train\nuses dataset + labels] --> C

    B:::io
    C:::io
    D:::io
    E:::io
    T:::io

    classDef io fill:#eef,stroke:#557,stroke-width:1px;
```

## Module Contracts (Phase 2 Reference)
| Module | Inputs | Outputs | Dependencies | Update rate |
|---|---|---|---|---|
| preprocess | `frame: (H,W,3) BGR uint8` | `lanes: (L,4) int32`, `roi: (H,W) uint8` | `numpy`, lane geometry config | per frame |
| model | `roi: (H,W) uint8` | `probs: (N,) float32`, `class_id: int` | model weights artifact | per frame |
| train | `dataset`, `labels`, `seed` | weights artifact, metrics json | dataset loader, optimizer config | offline batch |
| eval | `probs`, `class_id`, thresholds | `decision`, `reason_code` | reject profile config | per frame |
| deploy | `decision`, timing metadata | scheduled command payload | scheduler + transport interface | per frame |

## Phase 2 Tasks

Phase 2 actionable tasks were consolidated into the repository-wide canonical task list: [`TASKS.md`](../TASKS.md).

Use this document for Phase 2 scope context (module contracts and pipeline intent), and use `TASKS.md` for execution tracking and completion state.
