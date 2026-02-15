"""
Monitoring and observability for CAIRE Phase 1.

- Health check: DB connectivity, optional LLM connectivity
- Metrics: Prometheus-style /api/metrics (counts, compilation time, LLM cost, test pass rate)
- Used by /api/health and /api/metrics endpoints and the metrics dashboard
"""

import logging
import os
import time
from typing import Any, Optional

from backend.database import SessionLocal, engine
from backend.models_db import (
    CompileJobModel,
    DecisionTreeModel,
    GuidelineDocumentModel,
    LLMCallLog,
    TestCaseModel,
    TestResultModel,
)
from sqlalchemy import func, text

logger = logging.getLogger(__name__)


def check_db() -> tuple[bool, str]:
    """Check database connectivity. Returns (ok, message)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as e:
        return False, str(e)


def check_llm_config() -> tuple[bool, str]:
    """Check if LLM is configured (API key set). Does not call the API."""
    if os.getenv("OPENAI_API_KEY"):
        return True, "openai configured"
    if os.getenv("ANTHROPIC_API_KEY"):
        return True, "anthropic configured"
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return True, "gemini configured"
    return False, "no LLM API key set"


def get_health() -> dict[str, Any]:
    """Return health status for /api/health."""
    db_ok, db_msg = check_db()
    llm_ok, llm_msg = check_llm_config()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "checks": {
            "database": {"status": "up" if db_ok else "down", "message": db_msg},
            "llm_config": {"status": "configured" if llm_ok else "not_configured", "message": llm_msg},
        },
    }


def get_metrics() -> dict[str, Any]:
    """Aggregate metrics from DB for /api/metrics and dashboard."""
    db = SessionLocal()
    try:
        # If tables don't exist yet, return zeros
        guidelines_total = db.query(func.count(GuidelineDocumentModel.id)).scalar() or 0
        trees_total = db.query(func.count(DecisionTreeModel.id)).scalar() or 0
        test_cases_total = db.query(func.count(TestCaseModel.id)).scalar() or 0

        # Compilation jobs: completed count and average duration (if we had duration stored)
        jobs_completed = (
            db.query(func.count(CompileJobModel.id))
            .filter(CompileJobModel.status == "completed")
            .scalar() or 0
        )
        jobs_failed = (
            db.query(func.count(CompileJobModel.id))
            .filter(CompileJobModel.status == "failed")
            .scalar() or 0
        )

        # LLM cost and calls from LLMCallLog
        llm_stats = (
            db.query(
                func.count(LLMCallLog.id).label("calls"),
                func.coalesce(func.sum(LLMCallLog.estimated_cost_usd), 0).label("cost_usd"),
            )
        ).first()
        llm_calls = llm_stats.calls or 0
        llm_cost_usd = float(llm_stats.cost_usd or 0)

        # Test results: latest run per tree, aggregate pass rate
        # We don't have a single "pass rate over time" table; use latest test_results rows
        result_rows = (
            db.query(TestResultModel)
            .order_by(TestResultModel.run_at.desc())
            .limit(100)
            .all()
        )
        total_tests = 0
        total_passed = 0
        for row in result_rows:
            if row.results and isinstance(row.results, dict):
                total_tests += row.results.get("total") or 0
                total_passed += row.results.get("passed") or 0
        test_pass_rate = (total_passed / total_tests * 100) if total_tests else None

        return {
            "guidelines_processed": guidelines_total,
            "trees_compiled": trees_total,
            "compilations_completed": jobs_completed,
            "compilations_failed": jobs_failed,
            "test_cases_total": test_cases_total,
            "llm_api_calls": llm_calls,
            "llm_estimated_cost_usd": round(llm_cost_usd, 4),
            "test_runs_sampled": len(result_rows),
            "test_pass_rate_percent": round(test_pass_rate, 1) if test_pass_rate is not None else None,
        }
    except Exception as e:
        logger.exception("get_metrics failed: %s", e)
        return {
            "guidelines_processed": 0,
            "trees_compiled": 0,
            "compilations_completed": 0,
            "compilations_failed": 0,
            "test_cases_total": 0,
            "llm_api_calls": 0,
            "llm_estimated_cost_usd": 0.0,
            "test_runs_sampled": 0,
            "test_pass_rate_percent": None,
            "error": str(e),
        }
    finally:
        db.close()


def get_validation_error_counts() -> list[dict[str, Any]]:
    """Return most common validation error codes (from logs or a future validation_log table). Phase 1: placeholder."""
    # TODO: if we add a validation_log table, aggregate by code here
    return []
