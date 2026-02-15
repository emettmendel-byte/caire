"""Unit tests for the guideline-to-tree compiler."""

import pytest
from pathlib import Path

from backend.compiler import compile_guideline_to_tree, extract_text_from_pdf
from shared.schemas import NodeType


def test_compile_from_raw_text():
    tree = compile_guideline_to_tree(
        raw_text="Patient has fever. If fever > 38 go to emergency.",
        tree_id="t1",
        name="Fever triage",
    )
    assert tree.id == "t1"
    assert tree.name == "Fever triage"
    assert tree.root_id == "root"
    assert len(tree.nodes) >= 2
    assert len(tree.edges) >= 1
    types = [n.type for n in tree.nodes]
    assert NodeType.ROOT in types


def test_compile_no_input():
    tree = compile_guideline_to_tree(tree_id="empty", name="Empty")
    assert tree.id == "empty"
    assert tree.root_id == "root"


def test_extract_text_from_pdf_requires_pypdf2():
    """Without a real PDF we only check that the function exists and errors on missing file."""
    with pytest.raises(Exception):  # FileNotFoundError or RuntimeError
        extract_text_from_pdf(Path("/nonexistent/file.pdf"))
