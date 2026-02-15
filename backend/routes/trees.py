"""
CRUD and tree-generation routes for decision trees.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models_db import DecisionTreeModel
from backend.compiler import compile_guideline_to_tree
from shared.schemas import DecisionTree

router = APIRouter()

# Directory for versioned tree JSON files (optional storage)
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


@router.get("/", response_model=list[dict])
def list_trees(db: Session = Depends(get_db)):
    """List all decision trees (id, version, name, updated_at)."""
    rows = db.query(DecisionTreeModel).order_by(DecisionTreeModel.updated_at.desc()).all()
    return [
        {
            "id": r.id,
            "version": r.version,
            "name": r.name,
            "description": r.description,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/{tree_id}", response_model=DecisionTree)
def get_tree(tree_id: str, db: Session = Depends(get_db)):
    """Get a single decision tree by ID (from DB or from /models if not in DB)."""
    row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree_id).first()
    if row and row.tree_json:
        return DecisionTree.model_validate(row.tree_json)

    # Fallback: load from models/*.json
    if MODELS_DIR.exists():
        for path in MODELS_DIR.glob("*.json"):
            try:
                import json
                data = json.loads(path.read_text())
                if data.get("id") == tree_id:
                    return DecisionTree.model_validate(data)
            except Exception:
                continue

    raise HTTPException(status_code=404, detail=f"Tree '{tree_id}' not found")


@router.post("/", response_model=DecisionTree, status_code=201)
def create_tree(tree: DecisionTree, db: Session = Depends(get_db)):
    """Create or overwrite a decision tree."""
    row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree.id).first()
    payload = tree.model_dump(mode="json")
    if row:
        row.version = tree.version
        row.name = tree.name
        row.description = tree.description
        row.tree_json = payload
        db.commit()
        db.refresh(row)
        return tree
    row = DecisionTreeModel(
        id=tree.id,
        version=tree.version,
        name=tree.name,
        description=tree.description,
        tree_json=payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return tree


@router.put("/{tree_id}", response_model=DecisionTree)
def update_tree(tree_id: str, tree: DecisionTree, db: Session = Depends(get_db)):
    """Update an existing tree (ID in path must match body)."""
    if tree.id != tree_id:
        raise HTTPException(status_code=400, detail="ID in path and body must match")
    return create_tree(tree, db)


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
