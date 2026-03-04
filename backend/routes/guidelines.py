"""
Guideline ingestion API: upload, list, get by ID, full-text search.
"""

import uuid
from datetime import timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
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


def _iso_utc(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


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
            "processed_at": _iso_utc(r.processed_at),
            "created_at": _iso_utc(r.created_at),
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


@router.get("/{guideline_id}/file")
def get_guideline_file(guideline_id: str, db: Session = Depends(get_db)):
    """
    Download the original uploaded guideline file (PDF/Markdown) for preview in the frontend.
    """
    row = db.query(GuidelineDocumentModel).filter(GuidelineDocumentModel.id == guideline_id).first()
    if not row or not row.file_path:
        raise HTTPException(status_code=404, detail=f"Guideline '{guideline_id}' file not found")
    path = Path(row.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    # Only serve files within the guidelines directory
    try:
        base = GUIDELINES_DIR.resolve()
        resolved = path.resolve()
        if base not in resolved.parents and resolved != base:
            raise HTTPException(status_code=403, detail="Refusing to serve file outside guidelines directory")
    except Exception:
        raise HTTPException(status_code=403, detail="Refusing to serve file")
    media_type = "application/pdf" if resolved.suffix.lower() == ".pdf" else "text/plain"
    # IMPORTANT: do not set filename=... because it triggers Content-Disposition: attachment (download).
    # We want inline rendering in the browser PDF viewer.
    headers = {"Content-Disposition": f'inline; filename="{resolved.name}"'}
    return FileResponse(str(resolved), media_type=media_type, headers=headers)


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
    original_name = Path(file.filename or "file").name
    ext = Path(original_name).suffix.lower()
    if ext not in (".pdf", ".md", ".markdown"):
        raise HTTPException(status_code=400, detail="Only PDF and Markdown files are supported")
    safe_name = f"{doc_id}{ext}"
    path = GUIDELINES_DIR / safe_name

    content = await file.read()
    path.write_bytes(content)

    try:
        doc = process_guideline(str(path), domain=domain, guideline_id=doc_id)
        # Keep display name as uploaded filename (instead of internal random storage filename).
        row = db.query(GuidelineDocumentModel).filter(GuidelineDocumentModel.id == doc_id).first()
        if row and original_name:
            row.filename = original_name
            db.commit()
            db.refresh(row)
        return doc.model_dump(mode="json")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
