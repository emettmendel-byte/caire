"""
Test case execution and generation for decision tree validation.

- run_test_case: execute tree with inputs, trace path, compare to expected.
- run_all_tests: run full suite, aggregate, optional comparison to previous run.
- generate_test_cases: use student LLM to generate synthetic cases for coverage.
"""

import logging
import time
import uuid
from typing import Any, Optional, Union

from backend.models.decision_tree import (
    DecisionTree,
    DecisionNode,
    TestCase,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# TestResult model
# -----------------------------------------------------------------------------


def _exec_step(node_id: str, node_label: str, node_type: str, condition_evaluated: Optional[dict] = None, next_node_id: Optional[str] = None) -> dict:
    return {
        "node_id": node_id,
        "node_label": node_label,
        "node_type": node_type,
        "condition_evaluated": condition_evaluated,
        "next_node_id": next_node_id,
    }


class TestResult:
    """Result of running a single test case."""

    __slots__ = (
        "test_case_id",
        "passed",
        "actual_path",
        "expected_path",
        "actual_outcome",
        "expected_outcome",
        "execution_trace",
        "execution_time_ms",
        "error_message",
    )

    def __init__(
        self,
        test_case_id: str,
        passed: bool,
        actual_path: list[str],
        expected_path: list[str],
        actual_outcome: Optional[str],
        expected_outcome: Optional[str],
        execution_trace: list[dict],
        execution_time_ms: float,
        error_message: Optional[str] = None,
    ):
        self.test_case_id = test_case_id
        self.passed = passed
        self.actual_path = actual_path
        self.expected_path = expected_path
        self.actual_outcome = actual_outcome
        self.expected_outcome = expected_outcome
        self.execution_trace = execution_trace
        self.execution_time_ms = execution_time_ms
        self.error_message = error_message

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "passed": self.passed,
            "actual_path": self.actual_path,
            "expected_path": self.expected_path,
            "actual_outcome": self.actual_outcome,
            "expected_outcome": self.expected_outcome,
            "execution_trace": self.execution_trace,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
        }


class TestSuite:
    """Aggregated results of running all test cases for a tree."""

    def __init__(
        self,
        tree_id: str,
        results: list[TestResult],
        total: int,
        passed: int,
        failed: int,
        breaking_changes: Optional[list[str]] = None,
    ):
        self.tree_id = tree_id
        self.results = results
        self.total = total
        self.passed = passed
        self.failed = failed
        self.breaking_changes = breaking_changes or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "tree_id": self.tree_id,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "breaking_changes": self.breaking_changes,
            "results": [r.to_dict() for r in self.results],
        }


# -----------------------------------------------------------------------------
# Condition evaluation
# -----------------------------------------------------------------------------


def _evaluate_condition(
    value: Any,
    operator: str,
    threshold: Optional[Union[float, str, bool]],
) -> bool:
    """Evaluate a single condition. Returns True for 'match' / first branch."""
    if value is None and operator in ("present", "!=", "absent"):
        return operator == "absent"
    if value is None:
        return False
    op = (operator or "==").strip().lower()
    if op == "==":
        if threshold is None:
            return value is None
        return value == threshold
    if op == "!=":
        return value != threshold
    if op in ("<", ">", "<=", ">="):
        try:
            v = float(value) if not isinstance(value, (int, float)) else value
            t = float(threshold) if threshold is not None and not isinstance(threshold, (int, float)) else threshold
            if t is None:
                return False
            if op == "<":
                return v < t
            if op == ">":
                return v > t
            if op == "<=":
                return v <= t
            if op == ">=":
                return v >= t
        except (TypeError, ValueError):
            return False
    if op == "contains":
        return (threshold is not None and str(threshold) in str(value)) or (value is not None and str(value) in str(threshold or ""))
    if op == "present":
        return value is not None and value != ""
    if op == "absent":
        return value is None or value == ""
    return False


def _get_child_index(node: DecisionNode, inputs: dict[str, Any]) -> int:
    """For a condition node, return index of child to take (0 = first branch, 1 = second, etc.)."""
    if not node.children:
        return 0
    # Legacy "question" node without condition: use node id as variable, boolean → first child = true, second = false
    if not node.condition:
        value = inputs.get(node.id)
        if value in (True, "true", "yes", "Yes", 1):
            return 0
        return 1 if len(node.children) > 1 else 0
    c = node.condition
    value = inputs.get(c.variable)
    match = _evaluate_condition(value, c.operator, c.threshold)
    if match:
        return 0
    return 1 if len(node.children) > 1 else 0


# -----------------------------------------------------------------------------
# Tree execution
# -----------------------------------------------------------------------------


def run_test_case(tree: DecisionTree, test_case: TestCase) -> TestResult:
    """
    Execute the tree with test_case.input_values, trace path, compare to expected.
    """
    start = time.perf_counter()
    test_case_id = getattr(test_case, "id", str(uuid.uuid4()))
    inputs = dict(test_case.input_values or {})
    nodes = tree.nodes
    root_id = tree.root_node_id
    path: list[str] = []
    trace: list[dict] = []
    actual_outcome: Optional[str] = None
    error_message: Optional[str] = None

    try:
        if root_id not in nodes:
            error_message = f"Root node '{root_id}' not found"
            elapsed_ms = (time.perf_counter() - start) * 1000
            return TestResult(
                test_case_id=test_case_id,
                passed=False,
                actual_path=path,
                expected_path=list(test_case.expected_path or []),
                actual_outcome=None,
                expected_outcome=test_case.expected_outcome,
                execution_trace=trace,
                execution_time_ms=elapsed_ms,
                error_message=error_message,
            )

        current_id: Optional[str] = root_id
        while current_id:
            node = nodes.get(current_id)
            if not node:
                error_message = f"Node '{current_id}' not found"
                break
            path.append(current_id)
            label = getattr(node, "label", "") or node.id
            node_type = getattr(node.type, "value", str(node.type)) if hasattr(node.type, "value") else str(node.type)

            if node_type in ("action", "outcome"):
                actual_outcome = getattr(node.action, "recommendation", None) if node.action else label
                trace.append(_exec_step(current_id, label, node_type, None, None))
                break

            if node_type in ("condition", "question", "root") and node.condition:
                idx = _get_child_index(node, inputs)
                next_id = node.children[idx] if idx < len(node.children) else None
                cond = node.condition
                value = inputs.get(cond.variable)
                match = _evaluate_condition(value, cond.operator, cond.threshold)
                trace.append(
                    _exec_step(
                        current_id,
                        label,
                        node_type,
                        {
                            "variable": cond.variable,
                            "operator": cond.operator,
                            "threshold": cond.threshold,
                            "input_value": value,
                            "result": match,
                        },
                        next_id,
                    )
                )
                current_id = next_id
            else:
                # root or question without condition: take first child
                next_id = node.children[0] if node.children else None
                trace.append(_exec_step(current_id, label, node_type, None, next_id))
                current_id = next_id

    except Exception as e:
        logger.exception("run_test_case error")
        error_message = str(e)

    elapsed_ms = (time.perf_counter() - start) * 1000
    expected_path = list(test_case.expected_path or [])
    path_ok = (not expected_path) or (path == expected_path)
    outcome_ok = (not test_case.expected_outcome) or (
        actual_outcome is not None and test_case.expected_outcome.strip().lower() in (actual_outcome or "").strip().lower()
    )
    passed = path_ok and outcome_ok and error_message is None

    return TestResult(
        test_case_id=test_case_id,
        passed=passed,
        actual_path=path,
        expected_path=expected_path,
        actual_outcome=actual_outcome,
        expected_outcome=test_case.expected_outcome,
        execution_trace=trace,
        execution_time_ms=elapsed_ms,
        error_message=error_message,
    )


def run_all_tests(
    tree: DecisionTree,
    test_cases: list[TestCase],
    previous_results: Optional[list[dict]] = None,
) -> TestSuite:
    """Run all test cases; optionally compare to previous_results for breaking changes."""
    results: list[TestResult] = []
    for tc in test_cases:
        results.append(run_test_case(tree, tc))
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    breaking: list[str] = []
    if previous_results:
        prev_by_id = {r.get("test_case_id"): r for r in previous_results}
        for r in results:
            if not r.passed and prev_by_id.get(r.test_case_id, {}).get("passed"):
                breaking.append(f"Test {r.test_case_id} was passing, now failing")
    tree_id = getattr(tree, "id", "")
    if hasattr(tree_id, "hex"):
        tree_id = str(tree_id)
    return TestSuite(
        tree_id=str(tree_id),
        results=results,
        total=len(results),
        passed=passed,
        failed=failed,
        breaking_changes=breaking,
    )


# -----------------------------------------------------------------------------
# Test case generation (LLM)
# -----------------------------------------------------------------------------


async def generate_test_cases(tree: DecisionTree, count: int = 10) -> list[TestCase]:
    """Use student LLM to generate synthetic test cases aiming for branch coverage."""
    import json as _json
    from backend.services.llm_service import LLMRouter

    variables = tree.variables or []
    var_names = [v.name for v in variables]
    var_descriptions = {v.name: (v.description or f"{v.type}") for v in variables}
    node_list = list(tree.nodes.values())
    node_summary = [
        {"id": n.id, "type": getattr(n.type, "value", str(n.type)), "label": (n.label or "")[:80], "condition": getattr(n.condition, "variable", None) if n.condition else None}
        for n in node_list
    ]
    tree_id_str = str(tree.id) if hasattr(tree.id, "__str__") else tree.id

    prompt = f"""Generate exactly {count} test cases for this decision tree. Each test case must have:
- input_values: a JSON object with keys from the variable list below. Use realistic clinical values (numbers, booleans, or strings).
- expected_path: list of node IDs that should be traversed from root to the final action/outcome (optional but preferred).
- expected_outcome: the final recommendation text to expect (optional).

Variable names (use these as keys in input_values): {var_names}
Variable types/descriptions: {_json.dumps(var_descriptions)}

Nodes (id, type, label, condition variable): {_json.dumps(node_summary, indent=2)}

Include edge cases: boundary values (e.g. exactly at threshold), missing data (omit a variable or use null), and normal cases.
Return a JSON array of objects, each with keys: id (unique string), tree_id ("{tree_id_str}"), input_values, expected_path (array of node ids), expected_outcome (string or null).
No markdown, no explanation, only the JSON array."""

    router = LLMRouter()
    try:
        content, _ = await router.call_student_model(prompt, "You are a test data generator. Output only valid JSON.")
        # Strip markdown code block if present
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        data = _json.loads(text)
        if not isinstance(data, list):
            data = [data]
        cases: list[TestCase] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            tc_id = item.get("id") or f"gen-{uuid.uuid4().hex[:8]}"
            cases.append(
                TestCase(
                    id=tc_id,
                    tree_id=tree.id,
                    input_values=item.get("input_values") or {},
                    expected_path=item.get("expected_path") or [],
                    expected_outcome=item.get("expected_outcome"),
                )
            )
        return cases
    except Exception as e:
        logger.exception("generate_test_cases LLM error: %s", e)
        return []
