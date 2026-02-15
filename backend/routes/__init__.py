"""API routes for CAIRE backend."""

from fastapi import APIRouter

from backend.routes import compile as compile_routes
from backend.routes import guidelines, trees, test_results, monitoring

api_router = APIRouter(prefix="/api", tags=["api"])

api_router.include_router(monitoring.router)
api_router.include_router(trees.router, prefix="/trees", tags=["trees"])
api_router.include_router(test_results.router, prefix="/test-results", tags=["test-results"])
api_router.include_router(guidelines.router, prefix="/guidelines", tags=["guidelines"])
api_router.include_router(compile_routes.router, prefix="/compile", tags=["compile"])
