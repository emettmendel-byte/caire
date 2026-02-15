"""
SQLAlchemy ORM models for CAIRE (persisted in SQLite).

Stores decision trees and related metadata; full tree JSON can live in /models for versioning.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class DecisionTreeModel(Base):
    """Persisted decision tree record (metadata + optional snapshot)."""

    __tablename__ = "decision_trees"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)  # draft, published, archived
    domain: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    # Full tree as JSON (DMN-style: nodes dict, variables list, root_node_id)
    tree_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompileJobModel(Base):
    """Async compilation job: guideline -> decision tree."""

    __tablename__ = "compile_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    guideline_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)  # pending, in_progress, completed, failed
    progress_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    result_tree_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_raw_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_tree_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GuidelineDocumentModel(Base):
    """Processed guideline document with sections and metadata."""

    __tablename__ = "guideline_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sections_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # list of {section_type, title, content, page_number}
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 'metadata' is reserved by SQLAlchemy
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LLMCallLog(Base):
    """Log of LLM API calls for cost and usage monitoring."""

    __tablename__ = "llm_call_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # openai, anthropic
    model: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # teacher, student
    input_tokens: Mapped[int] = mapped_column(nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(nullable=False, default=0)
    estimated_cost_usd: Mapped[Optional[float]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TestCaseModel(Base):
    """Stored test case for a decision tree."""

    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    tree_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_values: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    expected_path: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # list of node ids
    expected_outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TestResultModel(Base):
    """Latest test run results per tree (one row per run)."""

    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tree_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    results: Mapped[dict] = mapped_column(JSON, nullable=False)  # TestSuite.to_dict() or {results: [...], total, passed, failed}
