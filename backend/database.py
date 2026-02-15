"""
SQLite database setup for CAIRE.

Uses SQLAlchemy with a single file (caire.db) for simplicity.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
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
