# OpenSpec v3 Protocol Compliance Matrix

| Requirement | Command/Code | Expected behavior | Validation |
|---|---|---|---|
| Known command dispatch | SET_MODE/SCHED/GET_STATE/RESET_QUEUE | ACK with metadata payload | `tests/test_protocol_compliance_v3.py::test_protocol_supports_all_v3_commands` |
| Unknown command handling | NACK-1 UNKNOWN_COMMAND | Reject unknown token | `tests/test_protocol_compliance_v3.py::test_nack_semantics_align_to_spec_codes_1_to_8` |
| Argument count mismatch | NACK-2 ARG_COUNT_MISMATCH | Reject wrong arg count | `tests/test_protocol_compliance_v3.py::test_nack_semantics_align_to_spec_codes_1_to_8` |
| Argument range mismatch | NACK-3 ARG_RANGE_ERROR | Reject lane > 21 and trigger range violations | `tests/test_protocol_compliance_v3.py::test_nack_semantics_align_to_spec_codes_1_to_8` |
| Argument type mismatch | NACK-4 ARG_TYPE_ERROR | Reject non-numeric lane/trigger | `tests/test_protocol_compliance_v3.py::test_nack_semantics_align_to_spec_codes_1_to_8` |
| Invalid mode transition | NACK-5 INVALID_MODE_TRANSITION | Disallow SAFE->AUTO | `tests/test_protocol_compliance_v3.py::test_nack_semantics_align_to_spec_codes_1_to_8` |
| Queue full handling | NACK-6 QUEUE_FULL | Reject enqueue when full | `tests/test_protocol_compliance_v3.py::test_nack_semantics_align_to_spec_codes_1_to_8` |
| Busy handling | NACK-7 BUSY | Return busy while host locked | `tests/test_protocol_compliance_v3.py::test_nack_semantics_align_to_spec_codes_1_to_8` |
| Malformed frame handling | NACK-8 MALFORMED_FRAME | Reject non-framed payload | `tests/test_protocol_compliance_v3.py::test_nack_semantics_align_to_spec_codes_1_to_8` |
| ACK metadata | ACK | Parse mode/queue_depth/scheduler_state/queue_cleared | `tests/test_protocol_compliance_v3.py::test_ack_metadata_parsing_mode_queue_scheduler_and_queue_cleared` |
| Queue clear on mode change | SET_MODE | queue auto-clear + queue_cleared true | `tests/test_protocol_compliance_v3.py::test_set_mode_transition_auto_clears_queue_and_safe_explicit_transition` |
| Transport timeout retry policy | timeout + retry | Retry attempts with OpenSpec backoff before timeout fault | `tests/test_serial_transport.py::test_serial_transport_retries_on_timeout_then_succeeds`, `tests/test_serial_transport.py::test_serial_transport_exhausts_retries_before_timeout_error` |
