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
| ID | Module | Task | Deterministic acceptance check |
|---|---|---|---|
| p2_preprocess_01 | preprocess | Freeze lane-boundary ordering and add explicit boundary invariants (`monotonic`, `fixed lane count`). | identical boundaries across repeated runs for fixed input and config. |
| p2_preprocess_02 | preprocess | Add explicit normalization contract docs (`range=[0,1]`, color format=BGR, device=cpu). | contract fields present and validated at runtime boundary. |
| p2_model_01 | model | Lock model input/output tensor metadata in typed interface. | shape mismatch fails fast with deterministic error text. |
| p2_model_02 | model | Add deterministic post-processing order for class tie handling. | tied logits always resolve to same `class_id`. |
| p2_train_01 | train | Enforce seeded pipeline for split/shuffle/augmentation. | identical seed yields identical artifact checksum. |
| p2_train_02 | train | Emit immutable training manifest (`seed`, dataset hash, config hash). | manifest hash stable for same run inputs. |
| p2_eval_01 | eval | Codify reject rule precedence and threshold binding order. | same inputs always produce identical `decision` and `reason_code`. |
| p2_eval_02 | eval | Add explicit unknown-class policy (`reject` vs `pass`) in profile. | profile validation rejects ambiguous policy. |
| p2_deploy_01 | deploy | Pin scheduler payload schema and field ordering. | payload serialization byte-stable for same decision input. |
| p2_deploy_02 | deploy | Add bounded-latency guardrails for command enqueue path. | enqueue path remains within configured deterministic limit. |

## Execution Order
1. `p2_preprocess_01`
2. `p2_preprocess_02`
3. `p2_model_01`
4. `p2_model_02`
5. `p2_train_01`
6. `p2_train_02`
7. `p2_eval_01`
8. `p2_eval_02`
9. `p2_deploy_01`
10. `p2_deploy_02`

## Exit Criteria
- All five modules expose explicit I/O contracts.
- Deterministic checks pass for repeated-input runs.
- Deploy payload and timing behavior remain byte-stable and bounded.
