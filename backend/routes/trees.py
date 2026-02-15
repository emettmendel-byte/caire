"""
CRUD and tree-generation routes for decision trees.
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models_db import DecisionTreeModel, TestCaseModel, TestResultModel
from backend.compiler import compile_guideline_to_tree
from backend.services.compiler_service import validate_tree_structure, validate_conditions
from backend.services.llm_service import refine_node
from backend.services.test_service import run_test_case, run_all_tests, generate_test_cases
from backend.models.decision_tree import DecisionTree as DMNTree, DecisionNode as DMNNode, TestCase
from shared.schemas import DecisionTree

router = APIRouter()

# Directory for versioned tree JSON files (optional storage)
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


def _is_dmn_shape(data: dict) -> bool:
    """True if tree_json is DMN-style (nodes dict, root_node_id)."""
    return isinstance(data.get("nodes"), dict) and "root_node_id" in data


@router.post("/seed-sample", status_code=201)
def seed_sample_tree(db: Session = Depends(get_db)):
    """Load the sample decision tree from models/sample_triage_v1.json into the database so it appears in the list."""
    sample_path = MODELS_DIR / "sample_triage_v1.json"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample file not found: models/sample_triage_v1.json")
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    tree_id = data.get("id", "sample-triage")
    row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree_id).first()
    if row:
        row.tree_json = data
        row.version = data.get("version", row.version)
        row.name = data.get("name", row.name)
        row.description = data.get("description")
        db.commit()
        db.refresh(row)
    else:
        row = DecisionTreeModel(
            id=tree_id,
            version=data.get("version", "1.0.0"),
            name=data.get("name", "Sample General Triage"),
            description=data.get("description"),
            status="draft",
            tree_json=data,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return {"id": row.id, "name": row.name, "version": row.version}


@router.get("/", response_model=list[dict])
def list_trees(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status (draft, published, archived)"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
):
    """List decision trees with optional filtering by status and domain."""
    q = db.query(DecisionTreeModel).order_by(DecisionTreeModel.updated_at.desc())
    if status:
        q = q.filter(DecisionTreeModel.status == status)
    if domain:
        q = q.filter(DecisionTreeModel.domain == domain)
    rows = q.all()
    return [
        {
            "id": r.id,
            "version": r.version,
            "name": r.name,
            "description": r.description,
            "status": getattr(r, "status", None) or "draft",
            "domain": getattr(r, "domain", None),
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/{tree_id}")
def get_tree(tree_id: str, db: Session = Depends(get_db)):
    """Get a single decision tree by ID. Returns stored JSON (supports both list+edges and DMN shapes)."""
    row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree_id).first()
    if row and row.tree_json:
        data = row.tree_json
        if _is_dmn_shape(data):
            return data
        return DecisionTree.model_validate(data)

    # Fallback: load from models/*.json
    if MODELS_DIR.exists():
        for path in MODELS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if data.get("id") == tree_id:
                    if _is_dmn_shape(data):
                        return data
                    return DecisionTree.model_validate(data)
            except Exception:
                continue

    raise HTTPException(status_code=404, detail=f"Tree '{tree_id}' not found")


@router.post("/", status_code=201)
def create_tree(tree: DecisionTree, db: Session = Depends(get_db)):
    """Create or overwrite a decision tree (list+edges schema)."""
    row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree.id).first()
    payload = tree.model_dump(mode="json")
    if row:
        row.version = tree.version
        row.name = tree.name
        row.description = tree.description
        row.tree_json = payload
        row.status = getattr(row, "status", None) or "draft"
        db.commit()
        db.refresh(row)
        return tree
    row = DecisionTreeModel(
        id=tree.id,
        version=tree.version,
        name=tree.name,
        description=tree.description,
        status="draft",
        tree_json=payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return tree


@router.put("/{tree_id}")
def update_tree(tree_id: str, tree: dict[str, Any], db: Session = Depends(get_db)):
    """Update an existing tree with full JSON body (supports DMN or legacy shape)."""
    if tree.get("id") and tree.get("id") != tree_id:
        raise HTTPException(status_code=400, detail="ID in path and body must match")
    tree["id"] = tree_id
    row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Tree '{tree_id}' not found")
    row.tree_json = tree
    row.version = tree.get("version", row.version)
    row.name = tree.get("name", row.name)
    row.description = tree.get("description")
    row.domain = tree.get("domain") if hasattr(row, "domain") else None
    db.commit()
    db.refresh(row)
    return tree


@router.post("/validate")
def validate_tree_body(tree: dict[str, Any]):
    """Run structure and condition validation on a tree (DMN shape). Returns list of errors."""
    try:
        dmn = DMNTree.model_validate(tree)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid tree: {e}") from e
    structure_errors = validate_tree_structure(dmn)
    condition_errors = validate_conditions(dmn)
    errors = [
        {"code": e.code, "message": e.message, "node_id": e.node_id, "path": e.path}
        for e in structure_errors + condition_errors
    ]
    return {"errors": errors, "valid": len(errors) == 0}


class RefineNodeBody(BaseModel):
    node_id: str = Field(..., description="ID of the node to refine")
    instruction: str = Field(..., description="Natural language instruction for the LLM")


@router.post("/{tree_id}/nodes/refine")
async def refine_tree_node(tree_id: str, body: RefineNodeBody, db: Session = Depends(get_db)):
    """Refine a single node using the LLM (student model). Returns the updated node."""
    row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree_id).first()
    if not row or not row.tree_json:
        raise HTTPException(status_code=404, detail=f"Tree '{tree_id}' not found")
    data = row.tree_json
    nodes = data.get("nodes") or {}
    if isinstance(nodes, list):
        nodes = {n["id"]: n for n in nodes if isinstance(n, dict)}
    node_data = nodes.get(body.node_id)
    if not node_data:
        raise HTTPException(status_code=404, detail=f"Node '{body.node_id}' not found")
    try:
        node = DMNNode.model_validate(node_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid node: {e}") from e
    refined = await refine_node(node, body.instruction)
    return refined.model_dump(mode="json")


# -----------------------------------------------------------------------------
# Test cases and test execution
# -----------------------------------------------------------------------------


def _load_tree_dmn(db: Session, tree_id: str) -> DMNTree:
    row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree_id).first()
    if not row or not row.tree_json:
        raise HTTPException(status_code=404, detail=f"Tree '{tree_id}' not found")
    data = row.tree_json
    if isinstance(data.get("nodes"), dict) and "root_node_id" in data:
        return DMNTree.model_validate(data)
    # Legacy: nodes list + edges; convert to DMN-like for execution
    if isinstance(data.get("nodes"), list) and "edges" in data:
        nodes_list = data["nodes"]
        edges = data.get("edges") or []
        root_id = data.get("root_id") or (nodes_list[0]["id"] if nodes_list else "")
        nodes_dict = {}
        for n in nodes_list:
            nid = n.get("id")
            if not nid:
                continue
            children = [e["target_id"] for e in edges if e.get("source_id") == nid]
            nodes_dict[nid] = {
                "id": nid,
                "type": n.get("type", "condition"),
                "label": n.get("label", nid),
                "condition": n.get("condition"),
                "action": n.get("action"),
                "children": children,
            }
        return DMNTree.model_validate({
            "id": data.get("id", tree_id),
            "name": data.get("name", "Tree"),
            "version": data.get("version", "1.0.0"),
            "domain": data.get("domain", "general"),
            "root_node_id": root_id,
            "nodes": nodes_dict,
            "variables": data.get("variables", []),
        })
    raise HTTPException(status_code=400, detail="Tree must be DMN or legacy (nodes list + edges) for testing")


class TestCaseCreate(BaseModel):
    input_values: dict[str, Any] = Field(default_factory=dict)
    expected_path: list[str] = Field(default_factory=list)
    expected_outcome: Optional[str] = None


@router.get("/{tree_id}/test-cases")
def list_test_cases(tree_id: str, db: Session = Depends(get_db)):
    """List all test cases for a tree."""
    rows = db.query(TestCaseModel).filter(TestCaseModel.tree_id == tree_id).order_by(TestCaseModel.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "tree_id": r.tree_id,
            "input_values": r.input_values or {},
            "expected_path": r.expected_path or [],
            "expected_outcome": r.expected_outcome,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/{tree_id}/test-cases", status_code=201)
def create_test_case(tree_id: str, body: TestCaseCreate, db: Session = Depends(get_db)):
    """Create a new test case for the tree."""
    tc_id = f"tc-{uuid.uuid4().hex[:12]}"
    row = TestCaseModel(
        id=tc_id,
        tree_id=tree_id,
        input_values=body.input_values,
        expected_path=body.expected_path,
        expected_outcome=body.expected_outcome,
    )
    db.add(row)
    db.commit()
    return {"id": tc_id, "tree_id": tree_id, "input_values": body.input_values, "expected_path": body.expected_path, "expected_outcome": body.expected_outcome}


@router.post("/{tree_id}/test-cases/generate", status_code=201)
async def generate_tree_test_cases(tree_id: str, count: int = 10, db: Session = Depends(get_db)):
    """Generate test cases using the student LLM; save and return them."""
    tree = _load_tree_dmn(db, tree_id)
    cases = await generate_test_cases(tree, count=count)
    created = []
    for tc in cases:
        row = TestCaseModel(
            id=tc.id,
            tree_id=tree_id,
            input_values=tc.input_values,
            expected_path=tc.expected_path,
            expected_outcome=tc.expected_outcome,
        )
        db.add(row)
        created.append({"id": tc.id, "tree_id": tree_id, "input_values": tc.input_values, "expected_path": tc.expected_path, "expected_outcome": tc.expected_outcome})
    db.commit()
    return created


@router.delete("/{tree_id}/test-cases/{case_id}", status_code=204)
def delete_test_case(tree_id: str, case_id: str, db: Session = Depends(get_db)):
    """Delete a test case."""
    row = db.query(TestCaseModel).filter(TestCaseModel.tree_id == tree_id, TestCaseModel.id == case_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Test case not found")
    db.delete(row)
    db.commit()
    return None


@router.post("/{tree_id}/test-cases/{case_id}/run")
def run_single_test(tree_id: str, case_id: str, db: Session = Depends(get_db)):
    """Run one test case and return its result."""
    tree = _load_tree_dmn(db, tree_id)
    row = db.query(TestCaseModel).filter(TestCaseModel.tree_id == tree_id, TestCaseModel.id == case_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Test case not found")
    tc = TestCase(id=row.id, tree_id=tree_id, input_values=row.input_values or {}, expected_path=row.expected_path or [], expected_outcome=row.expected_outcome)
    result = run_test_case(tree, tc)
    return result.to_dict()


@router.post("/{tree_id}/test/run-inline")
def run_inline_test(tree_id: str, body: TestCaseCreate, db: Session = Depends(get_db)):
    """Run a single test with inline payload (no save). Returns result."""
    tree = _load_tree_dmn(db, tree_id)
    tc = TestCase(id="inline", tree_id=tree_id, input_values=body.input_values, expected_path=body.expected_path, expected_outcome=body.expected_outcome)
    result = run_test_case(tree, tc)
    return result.to_dict()


@router.post("/{tree_id}/test")
def run_tests(tree_id: str, db: Session = Depends(get_db)):
    """Run all test cases for the tree; store and return results."""
    tree = _load_tree_dmn(db, tree_id)
    rows = db.query(TestCaseModel).filter(TestCaseModel.tree_id == tree_id).all()
    test_cases = [
        TestCase(id=r.id, tree_id=tree_id, input_values=r.input_values or {}, expected_path=r.expected_path or [], expected_outcome=r.expected_outcome)
        for r in rows
    ]
    previous = None
    last_run = db.query(TestResultModel).filter(TestResultModel.tree_id == tree_id).order_by(TestResultModel.run_at.desc()).first()
    if last_run and last_run.results and isinstance(last_run.results.get("results"), list):
        previous = last_run.results["results"]
    suite = run_all_tests(tree, test_cases, previous_results=previous)
    # Persist
    result_row = TestResultModel(tree_id=tree_id, results=suite.to_dict())
    db.add(result_row)
    db.commit()
    return suite.to_dict()


@router.delete("/{tree_id}", status_code=204)
def delete_tree(tree_id: str, db: Session = Depends(get_db)):
    """Delete a decision tree by ID."""
    row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Tree '{tree_id}' not found")
    db.delete(row)
    db.commit()
    return None


@router.post("/generate", response_model=DecisionTree, status_code=201)
async def generate_tree(
    name: Optional[str] = None,
    tree_id: Optional[str] = None,
    file: Optional[UploadFile] = None,
    db: Session = Depends(get_db),
):
    """
    Ingest a guideline (e.g. PDF upload) and generate a decision tree.
    Returns the generated tree and persists it if tree_id is provided.
    """
    source_path: Optional[Path] = None
    raw_text: Optional[str] = None
    if file:
        MODELS_DIR.parent.mkdir(parents=True, exist_ok=True)
        tmp = MODELS_DIR.parent / "guidelines"
        tmp.mkdir(parents=True, exist_ok=True)
        path = tmp / (file.filename or "upload")
        path.write_bytes(await file.read())
        if path.suffix.lower() == ".pdf":
            source_path = path
        else:
            raw_text = path.read_text(encoding="utf-8", errors="replace")
    tid = tree_id or "generated"
    tree = compile_guideline_to_tree(
        source_path=source_path, raw_text=raw_text, tree_id=tid, name=name or "Generated tree"
    )
    if tree_id:
        create_tree(tree, db)
    return tree
