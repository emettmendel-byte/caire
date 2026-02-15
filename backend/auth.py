"""
Phase 1 authentication: optional API key and rate limiting.

- If CAIRE_API_KEY is set, requests must include X-API-Key: <key> (or Authorization: Bearer <key>).
- Health and metrics can be excluded from auth for load balancers.
- Rate limiting: in-memory, per-IP or per-API-key; configurable requests per minute.
"""

import os
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery, HTTPBearer, HTTPAuthorizationCredentials

API_KEY_HEADER = "X-API-Key"
API_KEY_ENV = os.getenv("CAIRE_API_KEY", "").strip()
# Rate limit: max requests per window per identifier (IP or API key)
RATE_LIMIT_REQUESTS = int(os.environ.get("CAIRE_RATE_LIMIT_REQUESTS", "120"))
RATE_LIMIT_WINDOW_SEC = int(os.environ.get("CAIRE_RATE_LIMIT_WINDOW_SEC", "60"))

api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)
bearer = HTTPBearer(auto_error=False)

# In-memory rate limit: key -> (window_start_sec, count)
_rate_limit_store: dict[str, tuple[float, int]] = {}
_rate_limit_lock = None  # single-threaded; no lock for Phase 1


def _get_client_id(request: Request, api_key: Optional[str]) -> str:
    """Identify client for rate limiting: API key if present, else forwarded/X-Forwarded-For or client host."""
    if api_key:
        return f"key:{api_key[:16]}"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _check_rate_limit(client_id: str) -> None:
    """Raise 429 if over limit. Otherwise increment and allow."""
    if RATE_LIMIT_REQUESTS <= 0:
        return
    now = time.time()
    if client_id not in _rate_limit_store:
        _rate_limit_store[client_id] = (now, 1)
        return
    start, count = _rate_limit_store[client_id]
    if now - start >= RATE_LIMIT_WINDOW_SEC:
        _rate_limit_store[client_id] = (now, 1)
        return
    count += 1
    _rate_limit_store[client_id] = (start, count)
    if count > RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")


async def get_api_key(
    request: Request,
    header_key: Optional[str] = Security(api_key_header),
    query_key: Optional[str] = Security(api_key_query),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer),
) -> Optional[str]:
    """Extract API key from header, query, or Bearer token. Returns None if auth is disabled."""
    key = header_key or query_key or (credentials.credentials if credentials else None)
    if not API_KEY_ENV:
        # Auth disabled; still apply rate limit by IP
        _check_rate_limit(_get_client_id(request, None))
        return None
    if not key:
        raise HTTPException(status_code=401, detail="Missing API key. Provide X-API-Key header or api_key query.")
    if key != API_KEY_ENV:
        raise HTTPException(status_code=403, detail="Invalid API key.")
    _check_rate_limit(_get_client_id(request, key))
    return key


def skip_auth_path(path: str) -> bool:
    """Paths that do not require API key (health, metrics for load balancers)."""
    return path.rstrip("/") in ("/api/health", "/api/metrics", "/api/metrics/dashboard")
