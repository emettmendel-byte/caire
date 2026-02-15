"""Routes for retrieving stored test results."""

from fastapi import APIRouter, Depends, HTTPException

from backend.database import get_db
from backend.models_db import TestResultModel
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/{tree_id}")
def get_latest_test_results(tree_id: str, db: Session = Depends(get_db)):
    """Get the most recent test run results for a tree."""
    row = (
        db.query(TestResultModel)
        .filter(TestResultModel.tree_id == tree_id)
        .order_by(TestResultModel.run_at.desc())
        .first()
    )
    if not row:
        return {"tree_id": tree_id, "results": [], "total": 0, "passed": 0, "failed": 0, "run_at": None}
    data = row.results or {}
    data["run_at"] = row.run_at.isoformat()
    return data
