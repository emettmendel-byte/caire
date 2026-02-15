"""
Guideline-to-decision-tree compiler (stub).

Parses guideline documents (e.g. PDF) and produces a DecisionTree structure.
Extend this module with real NLP/rule extraction logic.
"""

from pathlib import Path
from typing import Optional

from shared.schemas import DecisionTree, DecisionNode, Edge, NodeType

# Optional: use PyPDF2 when processing PDFs
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None  # type: ignore


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from a PDF file."""
    if PdfReader is None:
        raise RuntimeError("PyPDF2 is required for PDF extraction. Install with: pip install PyPDF2")
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def compile_guideline_to_tree(
    source_path: Optional[Path] = None,
    raw_text: Optional[str] = None,
    tree_id: str = "generated",
    name: str = "Generated tree",
) -> DecisionTree:
    """
    Compile a guideline (PDF or raw text) into a decision tree.

    Currently returns a minimal placeholder tree. Replace with actual
    parsing/NLP logic to build nodes and edges from the guideline content.
    """
    if source_path and source_path.suffix.lower() == ".pdf":
        raw_text = extract_text_from_pdf(source_path)
    if not raw_text:
        raw_text = ""

    # Placeholder: single root and one outcome node
    root_id = "root"
    outcome_id = "outcome_1"
    nodes = [
        DecisionNode(id=root_id, type=NodeType.ROOT, label="Start triage", description="Begin assessment"),
        DecisionNode(id=outcome_id, type=NodeType.OUTCOME, label="Review guideline for full logic", description=raw_text[:500] if raw_text else None),
    ]
    edges = [
        Edge(source_id=root_id, target_id=outcome_id, label="Continue"),
    ]

    return DecisionTree(
        id=tree_id,
        version="0.1.0",
        name=name,
        description="Generated from guideline (placeholder logic)",
        nodes=nodes,
        edges=edges,
        root_id=root_id,
    )
