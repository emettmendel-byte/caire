"""
Compilation API: trigger guideline->tree compilation (async job) and check status.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models_db import CompileJobModel
from backend.services.compiler_service import CompilerOptions, run_compilation_job_sync

router = APIRouter()


class CompileRequest(BaseModel):
    guideline_id: str = Field(..., description="ID of the ingested guideline to compile")
    options: CompilerOptions | None = Field(None, description="Compiler options")


@router.post("/")
def trigger_compile(
    body: CompileRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Start a compilation job: guideline_id -> decision tree.
    Returns job_id; use GET /api/compile/{job_id}/status for progress.
    """
    from backend.services.ingestion_service import get_guideline_document

    guideline_id = body.guideline_id
    doc = get_guideline_document(guideline_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Guideline '{guideline_id}' not found")

    opts = body.options or CompilerOptions()
    job_id = str(uuid.uuid4())[:12]
    job = CompileJobModel(
        id=job_id,
        guideline_id=guideline_id,
        status="pending",
        progress_message="Queued",
    )
    db.add(job)
    db.commit()

    background_tasks.add_task(run_compilation_job_sync, job_id, guideline_id, opts)
    return {"job_id": job_id, "guideline_id": guideline_id, "status": "pending", "message": "Compilation started"}


@router.get("/{job_id}/status")
def get_compile_status(job_id: str, db: Session = Depends(get_db)):
    """Get compilation job status and result (tree_id when completed)."""
    job = db.query(CompileJobModel).filter(CompileJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return {
        "job_id": job.id,
        "guideline_id": job.guideline_id,
        "status": job.status,
        "progress_message": job.progress_message,
        "result_tree_id": job.result_tree_id,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }
