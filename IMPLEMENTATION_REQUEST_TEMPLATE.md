# Implementation Request Template

Use this template when requesting a feature implementation.

## Project Context
- **Project**: <brief description and goals>
- **Module/Path**: <file(s), package, or function>
- **Language**: <Python/Go/TypeScript/...>
- **Frameworks/Libraries**: <required dependencies>

## Requirements
Describe concrete behavior with examples.

### Functional Requirements
1. <requirement>
2. <requirement>

### Non-Functional Requirements
- Performance: <latency/throughput/memory targets>
- Security: <input validation, authz/authn, secret handling>
- Reliability: <retry behavior, failure modes>

### Input/Output Contract
- Input: <schema/types/examples>
- Output: <schema/types/examples>
- Error cases: <expected error handling>

## Constraints
- Backward compatibility: <yes/no and scope>
- External APIs/services: <details>
- Deployment/runtime constraints: <details>

## Definition of Done
- [ ] Implementation complete
- [ ] Unit tests for normal + edge cases
- [ ] Safety review completed (logic/security/performance)
- [ ] Documentation updated

## Requested Output Format
1. Task broken into sub-steps with success criteria.
2. Implementation for each sub-step.
3. Automated tests for each sub-step.
4. Cross-check correctness, performance, and safety.
5. Brief design rationale + risk/mitigation summary.


## Preflight Validation
Before sending a request, validate that placeholders are fully replaced:

```bash
python tools/validate_implementation_request.py <request_file.md>
```

Validation fails if bracket/angle-bracket placeholders remain, or if the `REQUIREMENTS BEGIN/END` block is empty.

## Example Prompt Block
```text
TASK
1. Break down the task into clear sub-steps with success criteria.
2. For each sub-step:
   • Provide detailed implementation
   • Add automated test cases
   • Cross-check correctness, performance, and safety

REQUIREMENTS BEGIN
<put concrete requirements here>
REQUIREMENTS END

SAFETY CHECK
After generating code, analyze for:
- Logical errors
- Security issues (injection, unsafe I/O, privilege escalation)
- Performance bottlenecks
Then revise if issues are found.
```
