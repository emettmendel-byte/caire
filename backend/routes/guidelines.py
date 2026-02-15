"""
Guideline ingestion API: upload, list, get by ID, full-text search.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models_db import GuidelineDocumentModel
from backend.services.ingestion_service import (
    process_guideline,
    get_guideline_document,
    search_guidelines_fulltext,
    GuidelineDocument,
)

router = APIRouter()

GUIDELINES_DIR = Path(__file__).resolve().parent.parent.parent / "guidelines"


@router.get("/")
def list_guidelines(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Full-text search query"),
):
    """
    List all guidelines. If `q` is provided, filter by full-text search on content.
    """
    if q:
        ids = search_guidelines_fulltext(q)
        if not ids:
            return []
        rows = db.query(GuidelineDocumentModel).filter(GuidelineDocumentModel.id.in_(ids)).order_by(GuidelineDocumentModel.created_at.desc()).all()
        # Preserve order from FTS/LIKE
        by_id = {r.id: r for r in rows}
        rows = [by_id[i] for i in ids if i in by_id]
    else:
        rows = db.query(GuidelineDocumentModel).order_by(GuidelineDocumentModel.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "filename": r.filename,
            "file_path": r.file_path,
            "domain": r.domain,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/{guideline_id}", response_model=GuidelineDocument)
def get_guideline(guideline_id: str):
    """
    Retrieve a single processed guideline by ID (structured JSON with sections).
    """
    doc = get_guideline_document(guideline_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Guideline '{guideline_id}' not found")
    return doc


@router.post("/upload")
async def upload_guideline(
    file: UploadFile,
    domain: str = Query("general", description="Clinical domain for the guideline"),
    db: Session = Depends(get_db),
):
    """
    Upload a guideline (PDF or Markdown). Runs the full ingestion pipeline:
    extract text → preprocess → segment into sections → store in DB.
    Returns the structured guideline document.
    """
    GUIDELINES_DIR.mkdir(parents=True, exist_ok=True)
    doc_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename or "file").suffix.lower()
    if ext not in (".pdf", ".md", ".markdown"):
        raise HTTPException(status_code=400, detail="Only PDF and Markdown files are supported")
    safe_name = f"{doc_id}{ext}"
    path = GUIDELINES_DIR / safe_name

    content = await file.read()
    path.write_bytes(content)

    try:
        doc = process_guideline(str(path), domain=domain, guideline_id=doc_id)
        return doc.model_dump(mode="json")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
