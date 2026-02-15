"""
CAIRE core data models (DMN-inspired).

These models define the canonical decision tree structure for compilation,
execution, and validation. For API/JSON contract with the frontend, see also
shared.schemas.
"""

from backend.models.decision_tree import (
    ActionSpec,
    ConditionSpec,
    DecisionNode,
    DecisionTree,
    DecisionVariable,
    NodeType,
    TestCase,
    VariableType,
    get_decision_tree_json_schema,
    write_decision_tree_schema_to_file,
)

__all__ = [
    "ActionSpec",
    "ConditionSpec",
    "DecisionNode",
    "DecisionTree",
    "DecisionVariable",
    "NodeType",
    "TestCase",
    "VariableType",
    "get_decision_tree_json_schema",
    "write_decision_tree_schema_to_file",
]
