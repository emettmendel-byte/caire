"""
Decision tree JSON schema and Pydantic models.

Used by both backend (compiler, API) and frontend (authoring UI).
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Type of node in the decision tree."""

    ROOT = "root"
    QUESTION = "question"
    CONDITION = "condition"
    OUTCOME = "outcome"
    ACTION = "action"


class Edge(BaseModel):
    """Directed edge from one node to another (answer -> next node)."""

    source_id: str = Field(..., description="ID of the source node")
    target_id: str = Field(..., description="ID of the target node")
    label: Optional[str] = Field(None, description="Answer or condition label (e.g. 'Yes', 'No', 'Fever > 38')")
    value: Optional[Any] = Field(None, description="Optional value for programmatic use")


class DecisionNode(BaseModel):
    """Single node in the decision tree."""

    id: str = Field(..., description="Unique node ID")
    type: NodeType = Field(..., description="Node type")
    label: str = Field(..., description="Display label / question text")
    description: Optional[str] = Field(None, description="Optional longer description or clinical note")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Extra metadata (e.g. guideline ref)")


class TreeNode(DecisionNode):
    """Node with optional children (for tree traversal)."""

    children: list["TreeNode"] = Field(default_factory=list, description="Child nodes")


class DecisionTree(BaseModel):
    """Full decision tree model (versioned, serializable)."""

    id: str = Field(..., description="Unique tree ID")
    version: str = Field(..., description="Semantic version (e.g. 1.0.0)")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Tree description or guideline source")
    nodes: list[DecisionNode] = Field(default_factory=list, description="All nodes in the tree")
    edges: list[Edge] = Field(default_factory=list, description="Edges between nodes")
    root_id: Optional[str] = Field(None, description="ID of the root node")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Tree-level metadata")

    model_config = {"extra": "allow"}
