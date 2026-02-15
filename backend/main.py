"""
CAIRE FastAPI application entrypoint.

Run with: uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
from backend.models_db import DecisionTreeModel, GuidelineDocumentModel, LLMCallLog, CompileJobModel, TestCaseModel, TestResultModel
from backend.routes import api_router


def ensure_dirs():
    """Create guidelines and models directories if missing."""
    for name in ("guidelines", "models"):
        (Path(__file__).resolve().parent.parent / name).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and dirs on startup."""
    from backend.database import migrate_guideline_documents_if_needed, migrate_decision_trees_if_needed
    ensure_dirs()
    Base.metadata.create_all(bind=engine)
    migrate_guideline_documents_if_needed()
    migrate_decision_trees_if_needed()
    yield
    # Shutdown: nothing to do for SQLite


app = FastAPI(
    title="CAIRE API",
    description="Clinical AI for Rule-based Execution – guideline-to-decision-tree compiler",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for local React dev (Vite default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"service": "CAIRE", "docs": "/docs", "api": "/api"}
