#!/usr/bin/env python3
"""
Run the emergency-triage example: load compiled tree and execute fixture test cases.

Usage (from project root):
  python scripts/demo.py

Output: formatted table of results and a short evaluation report.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODEL_PATH = ROOT / "models" / "emergency-triage-v1.json"
FIXTURES_PATH = ROOT / "tests" / "fixtures" / "emergency_triage_cases.json"
REPORT_PATH = ROOT / "models" / "emergency-triage-demo-report.txt"


def load_tree_dmn(data: dict):
    """Load tree from JSON; convert legacy nodes list + edges to DMN dict if needed."""
    from backend.models.decision_tree import DecisionTree

    nodes = data.get("nodes")
    edges = data.get("edges") or []
    if isinstance(nodes, list):
        nodes_dict = {}
        for n in nodes:
            if not isinstance(n, dict) or "id" not in n:
                continue
            nid = n["id"]
            children = [e["target_id"] for e in edges if e.get("source_id") == nid]
            node_type = n.get("type", "condition")
            if node_type in ("question", "root"):
                node_type = "condition"
            elif node_type == "outcome":
                node_type = "action"
            nodes_dict[nid] = {
                "id": nid,
                "type": node_type,
                "label": n.get("label", nid),
                "condition": n.get("condition"),
                "action": n.get("action") or ({"recommendation": n.get("label", nid)} if node_type == "action" else None),
                "children": children,
            }
        data = {**data, "nodes": nodes_dict}
    if "root_id" in data and "root_node_id" not in data:
        data["root_node_id"] = data.pop("root_id")
    data.setdefault("domain", "general")
    return DecisionTree.model_validate(data)


def main() -> None:
    if not MODEL_PATH.exists():
        print(f"Error: Tree not found at {MODEL_PATH}. Run: python scripts/ingest_example.py")
        sys.exit(1)
    if not FIXTURES_PATH.exists():
        print(f"Error: Fixtures not found at {FIXTURES_PATH}")
        sys.exit(1)

    from backend.models.decision_tree import TestCase
    from backend.services.test_service import run_test_case

    tree_data = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    tree = load_tree_dmn(tree_data)
    cases_data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    cases = [TestCase.model_validate(c) for c in cases_data]

    print(f"Tree: {tree.name} (id={tree.id})")
    print(f"Running {len(cases)} test cases...\n")

    results = []
    for tc in cases:
        r = run_test_case(tree, tc)
        results.append((tc, r))

    # Table
    col_id = 22
    col_pass = 6
    col_outcome = 36
    col_time = 10
    header = f"{'Case ID':<{col_id}} {'Pass':<{col_pass}} {'Actual outcome':<{col_outcome}} {'Time (ms)':<{col_time}}"
    print(header)
    print("-" * (col_id + col_pass + col_outcome + col_time))
    for tc, r in results:
        outcome = (r.actual_outcome or "")[: col_outcome - 2]
        print(f"{tc.id:<{col_id}} {'Yes' if r.passed else 'No':<{col_pass}} {outcome:<{col_outcome}} {r.execution_time_ms:<{col_time}.1f}")

    passed = sum(1 for _, r in results if r.passed)
    total = len(results)
    print()
    print(f"Summary: {passed}/{total} passed")

    # Report
    lines = [
        "CAIRE Emergency Triage Demo — Evaluation Report",
        "=" * 50,
        f"Tree: {MODEL_PATH}",
        f"Fixtures: {FIXTURES_PATH}",
        f"Total cases: {total}",
        f"Passed: {passed}",
        f"Failed: {total - passed}",
        "",
        "Failed cases:",
    ]
    for tc, r in results:
        if not r.passed:
            lines.append(f"  - {tc.id}: {r.error_message or 'path/outcome mismatch'}")
            if r.actual_path:
                lines.append(f"    Actual path: {' -> '.join(r.actual_path)}")
            if r.actual_outcome:
                lines.append(f"    Actual outcome: {r.actual_outcome[:80]}")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
