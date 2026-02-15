"""API routes for CAIRE backend."""

from fastapi import APIRouter

from backend.routes import guidelines, trees

api_router = APIRouter(prefix="/api", tags=["api"])

api_router.include_router(trees.router, prefix="/trees", tags=["trees"])
api_router.include_router(guidelines.router, prefix="/guidelines", tags=["guidelines"])
