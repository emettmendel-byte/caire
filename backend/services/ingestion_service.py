"""
Guideline ingestion pipeline: PDF/markdown → cleaned text → segmented sections → DB.

Processes clinical guideline documents for downstream LLM parsing into decision trees.
"""

import logging
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from backend.database import engine
from backend.models_db import GuidelineDocumentModel
from backend.database import SessionLocal

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# GuidelineSection model
# -----------------------------------------------------------------------------


class SectionType(str, Enum):
    """Logical section types for segmented guidelines."""

    POPULATION_CRITERIA = "population_criteria"
    TRIAGE_LOGIC = "triage_logic"
    RED_FLAGS = "red_flags"
    RECOMMENDATIONS = "recommendations"
    OTHER = "other"


class GuidelineSection(BaseModel):
    """A single logical section of a guideline."""

    section_type: SectionType = Field(..., description="Type of section")
    title: str = Field(..., description="Section heading/title")
    content: str = Field(..., description="Section body text")
    page_number: Optional[int] = Field(None, description="Page number for traceability (PDF)")


class GuidelineDocument(BaseModel):
    """Structured guideline document ready for LLM parsing."""

    id: str = Field(..., description="Unique document ID")
    filename: str = Field(..., description="Original filename")
    file_path: Optional[str] = Field(None, description="Path to stored file")
    domain: str = Field(..., description="Clinical domain")
    raw_text: str = Field(default="", description="Full extracted/cleaned text")
    sections: list[GuidelineSection] = Field(default_factory=list, description="Segmented sections")
    created_at: Optional[datetime] = Field(None, description="When ingested")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra metadata (e.g. flowcharts_detected)")

    model_config = {"extra": "allow"}


# -----------------------------------------------------------------------------
# Document ingestion (PDF, Markdown)
# -----------------------------------------------------------------------------


def ingest_pdf(file_path: str) -> str:
    """Extract text from a PDF file. Returns cleaned full text."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise RuntimeError("PyPDF2 is required for PDF ingestion. Install with: pip install PyPDF2")

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append((i + 1, text))

    raw = "\n\n".join(f"{t}" for _, t in pages)
    return preprocess_text(raw)


def ingest_markdown(file_path: str) -> str:
    """Read and preprocess a markdown guideline file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    raw = path.read_text(encoding="utf-8", errors="replace")
    return preprocess_text(raw)


# -----------------------------------------------------------------------------
# Pre-processing
# -----------------------------------------------------------------------------


def preprocess_text(text: str) -> str:
    """
    Clean extracted text: remove headers/footers, fix line breaks, normalize whitespace.
    """
    if not text or not text.strip():
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove common header/footer patterns (page numbers, document title repeated)
    text = re.sub(r"^\s*\d+\s*$/m", "", text)  # standalone number (page)
    text = re.sub(r"^Page\s+\d+\s+of\s+\d+\s*$/im", "", text)
    text = re.sub(r"^©.*$/m", "", text)  # copyright line
    # Trim each line and drop empty at start/end
    lines = [ln.strip() for ln in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def detect_flowcharts_or_tables(text: str) -> list[str]:
    """
    Detect possible flowcharts or decision tables in text (for manual review).
    Returns list of short descriptions (e.g. 'Possible flowchart at line 42').
    TODO: Future enhancement - integrate diagram/flowchart extraction (e.g. from PDF
    embedded images or structured tables). For now we do simple heuristics only.
    """
    findings = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Decision table pattern: "If X then Y" or "Yes/No" columns
        if re.search(r"\b(if|when|then)\b.*\b(then|→|->)\b", stripped, re.I):
            findings.append(f"Possible decision logic at line {i + 1}: {stripped[:60]}...")
        # Box-drawing or arrow-like
        if re.search(r"[│┌┐└┘├┤┬┴┼→←↑↓]|->|=>", stripped):
            findings.append(f"Possible flowchart/table at line {i + 1}")
    return findings[:20]  # cap for logging


def extract_structured_elements(text: str) -> dict[str, list[str]]:
    """Extract bullet lists and numbered steps from text for downstream use."""
    bullets = re.findall(r"^[\s]*[•\-*]\s+(.+)$", text, re.MULTILINE)
    numbered = re.findall(r"^[\s]*\d+[.)]\s+(.+)$", text, re.MULTILINE)
    return {"bullets": [b.strip() for b in bullets if b.strip()], "numbered_steps": [n.strip() for n in numbered if n.strip()]}


# -----------------------------------------------------------------------------
# Section segmentation
# -----------------------------------------------------------------------------


# Keywords that suggest section type (title or first line)
SECTION_TYPE_HINTS = {
    SectionType.POPULATION_CRITERIA: ["population", "inclusion", "exclusion", "eligible", "criteria", "patient selection", "target population"],
    SectionType.TRIAGE_LOGIC: ["triage", "assessment", "decision", "algorithm", "pathway", "flow", "classification", "severity"],
    SectionType.RED_FLAGS: ["red flag", "warning", "urgent", "emergency", "immediate", "danger", "alert", "critical"],
    SectionType.RECOMMENDATIONS: ["recommendation", "management", "treatment", "refer", "disposition", "action", "next step"],
}


def _infer_section_type(title: str, content_snippet: str) -> SectionType:
    """Infer section type from title and a snippet of content."""
    combined = (title + " " + content_snippet).lower()
    for st, keywords in SECTION_TYPE_HINTS.items():
        if any(kw in combined for kw in keywords):
            return st
    return SectionType.OTHER


def segment_guideline(text: str, page_boundaries: Optional[list[tuple[int, int]]] = None) -> list[GuidelineSection]:
    """
    Break guideline text into logical sections.
    Uses heading-like lines (all caps, or ## style, or short lines followed by body) to split.
    page_boundaries: optional list of (page_number, start_char_index) for page_number attribution.
    """
    if not text.strip():
        return []

    sections = []
    # Split on likely headings: line that looks like a title (short, or starts with ## or 1. etc.)
    # We use: lines that are either (a) markdown ## heading, (b) short all-caps line, (c) numbered section
    pattern = re.compile(
        r"^(?:(?:#{1,3}\s*)?(.+?)|([A-Z][A-Za-z\s]{2,60})$|^(?:(\d+)[.)]\s*)([A-Z].+?)$)",
        re.MULTILINE,
    )
    # Simpler: split by double newline and treat first line of each block as potential title
    blocks = re.split(r"\n\s*\n", text)
    current_page = 1
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        title = lines[0].strip() if lines else ""
        # Strip markdown # from title
        if title.startswith("#"):
            title = re.sub(r"^#+\s*", "", title).strip()
        content = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        if not content and len(lines) == 1:
            content = title
            title = "Section"

        # Heuristic: very long first line is probably not a title, use as content
        if len(title) > 120:
            content = block
            title = "Section"

        section_type = _infer_section_type(title, content[:300])
        sections.append(
            GuidelineSection(
                section_type=section_type,
                title=title,
                content=content,
                page_number=current_page,
            )
        )

    return sections


# -----------------------------------------------------------------------------
# Full-text search (SQLite FTS5)
# -----------------------------------------------------------------------------


_FTS_ENABLED: Optional[bool] = None


def _ensure_fts_table() -> bool:
    """Create FTS5 virtual table if it does not exist. Returns True if FTS is available."""
    global _FTS_ENABLED
    if _FTS_ENABLED is False:
        return False
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS guideline_fts USING fts5(guideline_id, content)"
            ))
            conn.commit()
        _FTS_ENABLED = True
        return True
    except Exception as e:
        logger.debug("FTS5 not available: %s", e)
        _FTS_ENABLED = False
        return False


def _fts_sync_after_insert(guideline_id: str, content: str) -> None:
    """Upsert into FTS table for full-text search (if FTS5 is available)."""
    if not _ensure_fts_table() or not content:
        return
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM guideline_fts WHERE guideline_id = :gid"), {"gid": guideline_id})
            conn.execute(
                text("INSERT INTO guideline_fts(guideline_id, content) VALUES (:gid, :content)"),
                {"gid": guideline_id, "content": content[:1_000_000]},
            )
            conn.commit()
    except Exception as e:
        logger.debug("FTS insert skipped: %s", e)


def search_guidelines_fulltext(query: str) -> list[str]:
    """Return list of guideline IDs matching the full-text query. Uses FTS5 or LIKE fallback."""
    if not query or not query.strip():
        return []
    q = query.strip()
    try:
        if _ensure_fts_table():
            from sqlalchemy import text
            with engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT guideline_id FROM guideline_fts WHERE guideline_fts MATCH :q"),
                    {"q": q},
                ).fetchall()
                return [r[0] for r in rows] if rows else []
        # Fallback: LIKE search on main table
        with engine.connect() as conn:
            from sqlalchemy import text
            rows = conn.execute(
                text("SELECT id FROM guideline_documents WHERE extracted_text LIKE :pat ORDER BY created_at DESC"),
                {"pat": f"%{q}%"},
            ).fetchall()
            return [r[0] for r in rows]
    except Exception as e:
        logger.warning("Full-text search failed: %s", e)
        return []


# -----------------------------------------------------------------------------
# Pipeline orchestration
# -----------------------------------------------------------------------------


def process_guideline(file_path: str, domain: str, guideline_id: Optional[str] = None) -> GuidelineDocument:
    """
    Full pipeline: ingest file → preprocess → segment → store in DB.
    Returns structured GuidelineDocument ready for LLM parsing.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        raw_text = ingest_pdf(file_path)
    elif suffix in (".md", ".markdown"):
        raw_text = ingest_markdown(file_path)
    else:
        # Try as text/markdown
        raw_text = ingest_markdown(file_path)

    # Pre-processing
    flowcharts_detected = detect_flowcharts_or_tables(raw_text)
    if flowcharts_detected:
        logger.info("Flowchart/table cues (manual review): %s", flowcharts_detected[:5])
    structured = extract_structured_elements(raw_text)
    sections = segment_guideline(raw_text)

    doc_id = guideline_id
    if not doc_id:
        import uuid
        doc_id = str(uuid.uuid4())[:8]

    metadata: dict[str, Any] = {
        "flowcharts_detected": flowcharts_detected,
        "bullets_count": len(structured.get("bullets", [])),
        "numbered_steps_count": len(structured.get("numbered_steps", [])),
    }

    doc = GuidelineDocument(
        id=doc_id,
        filename=path.name,
        file_path=str(path.resolve()),
        domain=domain,
        raw_text=raw_text,
        sections=sections,
        created_at=datetime.utcnow(),
        metadata=metadata,
    )

    # Store in database
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        row = db.query(GuidelineDocumentModel).filter(GuidelineDocumentModel.id == doc_id).first()
        sections_json = [s.model_dump(mode="json") for s in sections]
        if row:
            row.domain = domain
            row.extracted_text = raw_text
            row.sections_json = sections_json
            row.processed_at = now
            row.extra_metadata = {**(row.extra_metadata or {}), **metadata}
            db.commit()
            db.refresh(row)
        else:
            row = GuidelineDocumentModel(
                id=doc_id,
                filename=path.name,
                file_path=str(path.resolve()),
                domain=domain,
                extracted_text=raw_text,
                sections_json=sections_json,
                processed_at=now,
                extra_metadata=metadata,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        _fts_sync_after_insert(doc_id, raw_text)
    finally:
        db.close()

    return doc


def get_guideline_document(guideline_id: str) -> Optional[GuidelineDocument]:
    """Load a processed guideline from the database as GuidelineDocument."""
    db = SessionLocal()
    try:
        row = db.query(GuidelineDocumentModel).filter(GuidelineDocumentModel.id == guideline_id).first()
        if not row:
            return None
        sections = []
        for s in (row.sections_json or []):
            try:
                sections.append(GuidelineSection.model_validate(s))
            except Exception:
                pass
        return GuidelineDocument(
            id=row.id,
            filename=row.filename,
            file_path=row.file_path,
            domain=row.domain or "",
            raw_text=row.extracted_text or "",
            sections=sections,
            created_at=row.created_at,
            metadata=row.extra_metadata or {},
        )
    finally:
        db.close()
