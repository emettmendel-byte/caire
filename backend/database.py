"""
SQLite database setup for CAIRE.

Uses SQLAlchemy with a single file (caire.db) for simplicity.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Default: store DB in project root for easy backup/portability
DB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("CAIRE_DB_PATH", str(DB_DIR / "caire.db"))
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False},  # SQLite requirement for FastAPI
    echo=os.getenv("CAIRE_DB_ECHO", "0") == "1",  # Set CAIRE_DB_ECHO=1 to log SQL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency: yield a DB session and close it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_guideline_documents_if_needed():
    """Add new columns to guideline_documents if they exist in the model but not in the DB."""
    with engine.connect() as conn:
        r = conn.execute(text("PRAGMA table_info(guideline_documents)")).fetchall()
        existing = {row[1] for row in r}
    adds = [("domain", "TEXT"), ("sections_json", "TEXT"), ("processed_at", "DATETIME")]
    for col, ctype in adds:
        if col not in existing:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE guideline_documents ADD COLUMN {col} {ctype}"))
                conn.commit()


def migrate_decision_trees_if_needed():
    """Add status and domain columns to decision_trees if missing."""
    with engine.connect() as conn:
        r = conn.execute(text("PRAGMA table_info(decision_trees)")).fetchall()
        existing = {row[1] for row in r}
    if "status" not in existing:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE decision_trees ADD COLUMN status TEXT DEFAULT 'draft'"))
            conn.commit()
    if "domain" not in existing:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE decision_trees ADD COLUMN domain TEXT"))
            conn.commit()
