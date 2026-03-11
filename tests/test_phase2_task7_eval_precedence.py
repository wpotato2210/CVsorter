from __future__ import annotations

import ast
from pathlib import Path

RULES_PATH = Path("src/coloursorter/eval/rules.py")


def _parse_rules_module() -> ast.Module:
    return ast.parse(RULES_PATH.read_text(encoding="utf-8"), filename=str(RULES_PATH))


def _function(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Function {name} was not found in {RULES_PATH}")


def test_phase2_task7_rejection_rule_precedence_order_is_stable() -> None:
    module = _parse_rules_module()
    function_node = _function(module, "rejection_reason_for_object")

    ordered_reasons: list[str] = []
    for node in function_node.body:
        if isinstance(node, ast.If):
            return_stmt = node.body[0]
            if isinstance(return_stmt, ast.Return) and isinstance(return_stmt.value, ast.Constant):
                if isinstance(return_stmt.value.value, str):
                    ordered_reasons.append(return_stmt.value.value)

    assert ordered_reasons == [
        "infection_score_threshold",
        "curve_score_threshold",
        "size_mm_threshold",
        "classified_reject",
    ]


def test_phase2_task7_decision_outcome_order_is_context_then_rejection_then_accept() -> None:
    module = _parse_rules_module()
    function_node = _function(module, "decision_outcome_for_object")

    first_if = function_node.body[0]
    assert isinstance(first_if, ast.If)
    first_return = first_if.body[0]
    assert isinstance(first_return, ast.Return)
    assert isinstance(first_return.value, ast.Call)
    assert first_return.value.func.id == "DecisionOutcome"

    reject_if = function_node.body[2]
    assert isinstance(reject_if, ast.If)
    reject_return = reject_if.body[0]
    assert isinstance(reject_return, ast.Return)

    final_return = function_node.body[3]
    assert isinstance(final_return, ast.Return)


def test_phase2_task7_threshold_binding_prefers_runtime_thresholds_before_defaults() -> None:
    module = _parse_rules_module()
    function_node = _function(module, "_profile_value_for_key")

    first_if = function_node.body[0]
    assert isinstance(first_if, ast.If)

    condition_src = ast.unparse(first_if.test)
    assert condition_src == "thresholds is not None and key in thresholds"

    first_return = first_if.body[0]
    assert isinstance(first_return, ast.Return)
    assert ast.unparse(first_return.value) == "float(thresholds[key])"

    fallback_return = function_node.body[1]
    assert isinstance(fallback_return, ast.Return)
    assert ast.unparse(fallback_return.value) == "float(DEFAULT_REJECTION_THRESHOLDS[key])"
