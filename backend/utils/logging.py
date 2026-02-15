"""
Structured logging for CAIRE.

- Configurable level (DEBUG, INFO, WARN, ERROR)
- Writes to /logs/ directory (rotating file handler)
- Console handler for development
- Helpers for LLM call logging, compilation steps, validation results
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Default: project root / logs
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_LEVEL = os.getenv("CAIRE_LOG_LEVEL", "INFO").upper()
LOG_LLM_CONTENT = os.getenv("CAIRE_LOG_LLM_CONTENT", "0").lower() in ("1", "true", "yes")


def _ensure_log_dir() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR


def configure_logging(
    level: str = LOG_LEVEL,
    log_dir: Optional[Path] = None,
    log_to_console: bool = True,
) -> None:
    """Configure root and CAIRE loggers. Call once at app startup."""
    log_dir = log_dir or LOG_DIR
    _ensure_log_dir()
    level_value = getattr(logging, level, logging.INFO)

    # Use a single log file for the app (rotate by size in production if needed)
    log_file = log_dir / "caire.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level_value)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(level_value)
    # Avoid duplicate handlers when reloading
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(file_handler)
    if log_to_console:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level_value)
        console.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
        root.addHandler(console)

    # Backend namespace
    backend = logging.getLogger("backend")
    backend.setLevel(level_value)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module (e.g. backend.services.compiler_service)."""
    return logging.getLogger(name)


def log_llm_call(
    logger: logging.Logger,
    role: str,
    model: str,
    prompt_preview: str,
    response_preview: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    duration_sec: Optional[float] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Log an LLM call. Full prompt/response only if CAIRE_LOG_LLM_CONTENT=1."""
    payload = {
        "event": "llm_call",
        "role": role,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_sec": duration_sec,
        "prompt_preview": prompt_preview[:200] + "..." if len(prompt_preview) > 200 else prompt_preview,
        "response_preview": response_preview[:200] + "..." if len(response_preview) > 200 else response_preview,
    }
    if extra:
        payload.update(extra)
    if LOG_LLM_CONTENT:
        payload["prompt_full"] = prompt_preview
        payload["response_full"] = response_preview
    logger.info("LLM call: %s", json.dumps(payload, default=str))


def log_compilation_step(
    logger: logging.Logger,
    step: str,
    guideline_id: str,
    duration_sec: Optional[float] = None,
    success: bool = True,
    error: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Log a compilation step (e.g. retrieve_guideline, llm_parse, validate)."""
    payload = {
        "event": "compilation_step",
        "step": step,
        "guideline_id": guideline_id,
        "duration_sec": duration_sec,
        "success": success,
        "error": error,
        "ts": datetime.utcnow().isoformat() + "Z",
    }
    if extra:
        payload.update(extra)
    if success:
        logger.info("Compilation: %s", json.dumps(payload, default=str))
    else:
        logger.warning("Compilation: %s", json.dumps(payload, default=str))


def log_validation_result(
    logger: logging.Logger,
    tree_id: str,
    structure_errors: int,
    condition_errors: int,
    duration_sec: Optional[float] = None,
) -> None:
    """Log validation run result."""
    payload = {
        "event": "validation",
        "tree_id": tree_id,
        "structure_errors": structure_errors,
        "condition_errors": condition_errors,
        "duration_sec": duration_sec,
        "ts": datetime.utcnow().isoformat() + "Z",
    }
    level = logging.WARNING if (structure_errors or condition_errors) else logging.INFO
    logger.log(level, "Validation: %s", json.dumps(payload, default=str))
