"""
DMN-inspired decision tree data model for CAIRE.

Based on Decision Model and Notation: decision points (condition/action/score),
clinical variables with terminology mapping, and test cases for validation.
All models are Pydantic v2 and support JSON schema generation.
"""

import json
from datetime import date, datetime
from pathlib import Path
from enum import Enum
from typing import Any, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------


class NodeType(str, Enum):
    """Type of decision point in the tree."""

    CONDITION = "condition"
    ACTION = "action"
    SCORE = "score"


class VariableType(str, Enum):
    """Type of a clinical variable."""

    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"


# -----------------------------------------------------------------------------
# Condition and action specs (for DecisionNode)
# -----------------------------------------------------------------------------


class ConditionSpec(BaseModel):
    """Specification for a condition node: variable, operator, threshold/value."""

    variable: str = Field(..., description="Name of the variable (must exist in tree variables)")
    operator: str = Field(
        ...,
        description="Comparison operator: '>', '<', '>=', '<=', '==', '!=', 'in', 'not_in', 'present', 'absent'",
    )
    threshold: Optional[Union[float, str, bool]] = Field(
        None,
        description="Threshold or value for comparison (numeric, category code, or boolean)",
    )
    unit: Optional[str] = Field(None, description="Unit of measure when relevant (e.g. 'mmHg')")

    model_config = {"extra": "forbid"}


class ActionSpec(BaseModel):
    """Specification for an action node: recommendation and urgency."""

    recommendation: str = Field(..., description="Human-readable recommendation or disposition text")
    urgency_level: Optional[Literal["emergency", "urgent", "routine", "deferred", "other"]] = Field(
        None,
        description="Urgency of the recommended action",
    )
    code: Optional[str] = Field(None, description="Structured code or protocol reference")

    model_config = {"extra": "forbid"}


# -----------------------------------------------------------------------------
# Node metadata (guideline source, evidence)
# -----------------------------------------------------------------------------


class NodeMetadata(BaseModel):
    """Metadata attached to a decision node (source, evidence, dates)."""

    source_guideline_section: Optional[str] = Field(None, description="Section or page reference in source guideline")
    evidence_grade: Optional[str] = Field(None, description="Evidence grade (e.g. 1A, 2B) if applicable")
    date: Optional[datetime] = Field(None, description="Date of last review or extraction")

    model_config = {"extra": "allow"}


# -----------------------------------------------------------------------------
# DecisionNode
# -----------------------------------------------------------------------------


class DecisionNode(BaseModel):
    """
    A single decision point in the tree (DMN-style).

    - condition: branching logic (variable, operator, threshold)
    - action: recommendation and urgency (for leaf/action nodes)
    - score: placeholder for future score/aggregation nodes
    - children: IDs of child nodes (next steps)
    """

    id: str = Field(..., description="Unique identifier for this node")
    type: NodeType = Field(..., description="Node type: condition, action, or score")
    label: str = Field(..., description="Human-readable description of the decision point")

    condition: Optional[ConditionSpec] = Field(
        None,
        description="For condition nodes: variable, operator, threshold",
    )
    action: Optional[ActionSpec] = Field(
        None,
        description="For action nodes: recommendation text and urgency level",
    )
    score_expression: Optional[str] = Field(
        None,
        description="For score nodes: expression or formula (e.g. 'HEART_score')",
    )

    children: list[str] = Field(
        default_factory=list,
        description="List of child node IDs (ordered: first match typically first branch)",
    )

    metadata: Optional[Union[NodeMetadata, dict[str, Any]]] = Field(
        default_factory=dict,
        description="Source guideline section, evidence grade, date",
    )

    model_config = {"extra": "allow"}


# -----------------------------------------------------------------------------
# DecisionVariable
# -----------------------------------------------------------------------------


class DecisionVariable(BaseModel):
    """Clinical variable used in the decision tree (inputs and intermediate values)."""

    name: str = Field(..., description="Variable name (e.g. 'age', 'chest_pain_severity')")
    type: VariableType = Field(..., description="Numeric, boolean, or categorical")
    units: Optional[str] = Field(None, description="Unit of measure (e.g. 'years', 'mmHg')")
    terminology_mapping: Optional[dict[str, Union[list[str], str]]] = Field(
        default_factory=dict,
        description="Codes from terminologies (e.g. SNOMED CT, LOINC): {'SNOMED': ['...'], 'LOINC': '...'}",
    )
    source: Optional[str] = Field(
        None,
        description="Where the data comes from: e.g. 'patient_history', 'vital_signs', 'lab'",
    )
    description: Optional[str] = Field(None, description="Human-readable description")

    model_config = {"extra": "allow"}


# -----------------------------------------------------------------------------
# Tree-level metadata
# -----------------------------------------------------------------------------


class TreeMetadata(BaseModel):
    """Metadata for the full decision tree."""

    guideline_source: Optional[str] = Field(None, description="Source guideline or document")
    created_date: Optional[datetime] = Field(None, description="When the tree was created")
    authors: list[str] = Field(default_factory=list, description="Authors or contributors")
    approval_status: Optional[str] = Field(None, description="e.g. 'draft', 'approved', 'retired'")

    model_config = {"extra": "allow"}


# -----------------------------------------------------------------------------
# DecisionTree
# -----------------------------------------------------------------------------


class DecisionTree(BaseModel):
    """
    Complete DMN-style decision tree model.

    Nodes are stored as a dict (node_id -> DecisionNode). Variables define
    the clinical inputs and any intermediate concepts. root_node_id points
    to the entry node.
    """

    id: Union[UUID, str] = Field(..., description="Unique tree identifier (UUID or string)")
    name: str = Field(..., description="Human-readable name (e.g. 'Emergency Department Chest Pain Triage')")
    version: str = Field(..., description="Semantic version (e.g. '1.0.0')")
    domain: str = Field(..., description="Clinical domain (e.g. 'emergency_triage', 'cardiology')")

    root_node_id: str = Field(..., description="ID of the root decision node")
    nodes: dict[str, DecisionNode] = Field(
        default_factory=dict,
        description="Map of node_id -> DecisionNode",
    )
    variables: list[DecisionVariable] = Field(
        default_factory=list,
        description="Clinical variables used in the tree",
    )

    metadata: Optional[Union[TreeMetadata, dict[str, Any]]] = Field(
        default_factory=dict,
        description="Guideline source, created date, authors, approval status",
    )

    model_config = {"extra": "allow"}


# -----------------------------------------------------------------------------
# TestCase (validation)
# -----------------------------------------------------------------------------


class TestCase(BaseModel):
    """A single test case for validating a decision tree."""

    id: str = Field(..., description="Unique test case ID")
    tree_id: Union[UUID, str] = Field(..., description="ID of the tree this case tests")
    input_values: dict[str, Optional[Union[float, bool, str]]] = Field(
        default_factory=dict,
        description="Variable name -> value (must match tree variables)",
    )
    expected_path: list[str] = Field(
        default_factory=list,
        description="Ordered list of node IDs that should be traversed",
    )
    expected_outcome: Optional[str] = Field(
        None,
        description="Final recommendation or action text to assert",
    )

    model_config = {"extra": "allow"}


# -----------------------------------------------------------------------------
# JSON Schema (versioned, for validation and docs)
# -----------------------------------------------------------------------------

SCHEMA_VERSION = "1.0.0"


def get_decision_tree_json_schema() -> dict[str, Any]:
    """
    Return the full JSON schema for the decision tree model.
    Root is a DecisionTree; $defs include all nested types and TestCase.
    Use for validation and versioned schema export.
    """
    tree_schema = DecisionTree.model_json_schema()
    test_schema = TestCase.model_json_schema()
    defs = {**(tree_schema.get("$defs", {})), **(test_schema.get("$defs", {}))}
    # Root describes a DecisionTree document
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://caire.example/schemas/decision_tree.json",
        "title": "CAIRE Decision Tree Schema",
        "description": "DMN-inspired decision tree model for clinical triage (CAIRE)",
        "version": SCHEMA_VERSION,
        **{k: v for k, v in tree_schema.items() if k not in ("$defs", "$schema", "$id", "title", "description")},
        "$defs": defs,
    }


def write_decision_tree_schema_to_file(path: Optional[Union[str, Path]] = None) -> Path:
    """
    Write the current decision tree JSON schema to a file for versioning and validation.
    Default path: project root / shared/schemas/decision_tree_schema.json
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent.parent / "shared" / "schemas" / "decision_tree_schema.json"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = get_decision_tree_json_schema()
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return path
