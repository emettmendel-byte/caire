"""
CAIRE FastAPI application entrypoint.

Run with: uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.auth import (
    API_KEY_ENV,
    API_KEY_HEADER,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SEC,
    skip_auth_path,
    _check_rate_limit,
    _get_client_id,
)
from backend.database import Base, engine
from backend.models_db import (
    CompileJobModel,
    DecisionTreeModel,
    GuidelineDocumentModel,
    LLMCallLog,
    TestCaseModel,
    TestResultModel,
)
from backend.routes import api_router
from backend.utils.logging import configure_logging

# PHI / HIPAA: Phase 1 must NOT be used with real PHI. See docs and .env.example.
# TODO: future phases — encryption at rest, BAA, access controls.


def ensure_dirs():
    """Create guidelines, models, and logs directories if missing."""
    root = Path(__file__).resolve().parent.parent
    for name in ("guidelines", "models", "logs"):
        (root / name).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables, dirs, and configure logging on startup."""
    from backend.database import migrate_guideline_documents_if_needed, migrate_decision_trees_if_needed

    ensure_dirs()
    configure_logging()
    Base.metadata.create_all(bind=engine)
    migrate_guideline_documents_if_needed()
    migrate_decision_trees_if_needed()
    yield
    # Shutdown: nothing to do for SQLite


app = FastAPI(
    title="CAIRE API",
    description="""Clinical AI for Rule-based Execution – guideline-to-decision-tree compiler.

## Authentication (Phase 1)
When `CAIRE_API_KEY` is set, include it in requests:
- **Header:** `X-API-Key: your-key`
- **Query:** `?api_key=your-key`
- **Bearer:** `Authorization: Bearer your-key`

Endpoints `/api/health` and `/api/metrics` do not require a key (for load balancers).

## Rate limiting
Configurable via `CAIRE_RATE_LIMIT_REQUESTS` (default 120) per `CAIRE_RATE_LIMIT_WINDOW_SEC` (default 60). 429 when exceeded.
""",
    version="0.1.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

# OpenAPI security scheme for API key (documentation only; enforcement is in middleware)
from fastapi.openapi.utils import get_openapi
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyHeader": {"type": "apiKey", "in": "header", "name": "X-API-Key", "description": "Set CAIRE_API_KEY in env to enforce"},
        "ApiKeyQuery": {"type": "apiKey", "in": "query", "name": "api_key"},
    }
    openapi_schema["security"] = [{"ApiKeyHeader": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema
app.openapi = custom_openapi

# CORS for local React dev (Vite default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthAndRateLimitMiddleware(BaseHTTPMiddleware):
    """Optional API key auth and rate limiting for /api/*."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)
        client_id = _get_client_id(request, request.headers.get(API_KEY_HEADER))
        try:
            _check_rate_limit(client_id)
        except Exception as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})
        if API_KEY_ENV and not skip_auth_path(path):
            key = request.headers.get(API_KEY_HEADER) or request.query_params.get("api_key")
            auth = request.headers.get("Authorization")
            if auth and auth.startswith("Bearer "):
                key = key or auth[7:]
            if not key:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=401, content={"detail": "Missing API key. Provide X-API-Key or api_key."})
            if key != API_KEY_ENV:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=403, content={"detail": "Invalid API key."})
        return await call_next(request)


app.add_middleware(AuthAndRateLimitMiddleware)
app.include_router(api_router)


@app.get("/")
def root():
    return {"service": "CAIRE", "docs": "/docs", "api": "/api"}
