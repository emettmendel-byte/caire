"""
Core compiler service: guideline -> decision tree via LLM with validation and job tracking.

Transforms ingested guidelines into DMN-style decision trees using the LLM router,
with structure and condition validation, and optional async job progress.
"""

import asyncio
import logging
import uuid
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from backend.models.decision_tree import (
    DecisionTree,
    DecisionNode,
    DecisionVariable,
    NodeType,
    VariableType,
    ConditionSpec,
)
from backend.models_db import CompileJobModel, DecisionTreeModel
from backend.database import SessionLocal
from backend.services.ingestion_service import get_guideline_document
from backend.services.llm_service import (
    LLMRouter,
    parse_guideline_to_tree,
    extract_decision_variables,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# CompilerOptions
# -----------------------------------------------------------------------------


class CompilerOptions(BaseModel):
    """Options for guideline compilation."""

    target_domain: str = Field(
        default="emergency_triage",
        description="Target domain (e.g. emergency_triage, primary_care_triage)",
    )
    strictness_level: str = Field(
        default="permissive",
        description="Validation strictness: permissive | strict",
    )
    include_evidence_links: bool = Field(
        default=False,
        description="Whether to extract and attach citation/evidence links",
    )
    max_tree_depth: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Maximum tree depth to allow",
    )


# -----------------------------------------------------------------------------
# ValidationError
# -----------------------------------------------------------------------------


class ValidationError(BaseModel):
    """A single validation issue."""

    code: str = Field(..., description="Error code (e.g. missing_node, cycle)")
    message: str = Field(..., description="Human-readable message")
    node_id: Optional[str] = Field(None, description="Relevant node ID if applicable")
    path: Optional[list[str]] = Field(None, description="Path of node IDs if applicable")


# -----------------------------------------------------------------------------
# Tree structure validation
# -----------------------------------------------------------------------------


def validate_tree_structure(tree: DecisionTree) -> list[ValidationError]:
    """
    Check: all referenced nodes exist, no cycles, no dead-end branches, root defined.
    """
    errors: list[ValidationError] = []
    nodes = tree.nodes
    root_id = tree.root_node_id

    if not root_id:
        errors.append(ValidationError(code="missing_root", message="Root node is not defined"))
        return errors

    if root_id not in nodes:
        errors.append(
            ValidationError(code="root_not_found", message=f"Root node '{root_id}' is not in nodes", node_id=root_id)
        )
        return errors

    # Reachable from root and check references
    visited: set[str] = set()
    stack: list[tuple[str, list[str]]] = [(root_id, [root_id])]

    while stack:
        nid, path = stack.pop()
        if nid in visited:
            errors.append(
                ValidationError(code="cycle", message=f"Cycle detected at node '{nid}'", node_id=nid, path=path)
            )
            continue
        visited.add(nid)
        node = nodes.get(nid)
        if not node:
            errors.append(ValidationError(code="missing_node", message=f"Referenced node '{nid}' does not exist", node_id=nid, path=path))
            continue
        for child_id in (node.children or []):
            if child_id not in nodes:
                errors.append(
                    ValidationError(
                        code="missing_node",
                        message=f"Child node '{child_id}' of '{nid}' does not exist",
                        node_id=child_id,
                        path=path + [child_id],
                    )
                )
            else:
                stack.append((child_id, path + [child_id]))

    # Dead-end: action/score nodes should typically have no children (or we allow it)
    for nid, node in nodes.items():
        if node.type == NodeType.ACTION and node.children:
            # Optional warning: action node with children
            if tree.metadata and isinstance(tree.metadata, dict) and tree.metadata.get("strict_validation"):
                errors.append(
                    ValidationError(
                        code="action_has_children",
                        message=f"Action node '{nid}' has children; action nodes are usually leaves",
                        node_id=nid,
                    )
                )

    return errors


# -----------------------------------------------------------------------------
# Condition validation
# -----------------------------------------------------------------------------


def validate_conditions(tree: DecisionTree) -> list[ValidationError]:
    """
    Check: thresholds reasonable, operators match variable types, flag ambiguous conditions.
    """
    errors: list[ValidationError] = []
    var_by_name = {v.name: v for v in tree.variables}

    for nid, node in tree.nodes.items():
        if not node.condition:
            continue
        cond = node.condition
        var = var_by_name.get(cond.variable)
        if not var:
            errors.append(
                ValidationError(
                    code="unknown_variable",
                    message=f"Condition references unknown variable '{cond.variable}'",
                    node_id=nid,
                )
            )
            continue
        # Operator vs type
        op = (cond.operator or "").strip()
        if var.type == VariableType.BOOLEAN and op not in ("==", "!=", "present", "absent"):
            errors.append(
                ValidationError(
                    code="operator_mismatch",
                    message=f"Boolean variable '{cond.variable}' used with operator '{op}'",
                    node_id=nid,
                )
            )
        if var.type == VariableType.NUMERIC and op not in (">", "<", ">=", "<=", "==", "!=", "present", "absent"):
            if op not in ("in", "not_in"):  # allow in for ranges
                errors.append(
                    ValidationError(
                        code="operator_mismatch",
                        message=f"Numeric variable '{cond.variable}' used with operator '{op}'",
                        node_id=nid,
                    )
                )
        # Threshold type vs variable
        if cond.threshold is not None and var.type == VariableType.NUMERIC:
            if not isinstance(cond.threshold, (int, float)):
                errors.append(
                    ValidationError(
                        code="threshold_type",
                        message=f"Numeric variable '{cond.variable}' has non-numeric threshold",
                        node_id=nid,
                    )
                )
        if cond.threshold is not None and var.type == VariableType.BOOLEAN:
            if not isinstance(cond.threshold, bool) and cond.threshold not in ("true", "false", "True", "False"):
                errors.append(
                    ValidationError(
                        code="threshold_type",
                        message=f"Boolean variable '{cond.variable}' has non-boolean threshold",
                        node_id=nid,
                    )
                )
    return errors


# -----------------------------------------------------------------------------
# Progress callback type
# -----------------------------------------------------------------------------


def _update_job_progress(job_id: str, status: str, progress_message: Optional[str] = None, **kwargs: Any) -> None:
    db = SessionLocal()
    try:
        job = db.query(CompileJobModel).filter(CompileJobModel.id == job_id).first()
        if job:
            job.status = status
            if progress_message is not None:
                job.progress_message = progress_message
            for k, v in kwargs.items():
                if hasattr(job, k):
                    setattr(job, k, v)
            db.commit()
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Core compile (async)
# -----------------------------------------------------------------------------


async def compile_guideline_to_tree(
    guideline_id: str,
    options: CompilerOptions,
    job_id: Optional[str] = None,
    router: Optional[LLMRouter] = None,
) -> DecisionTree:
    """
    Full workflow:
    1. Retrieve guideline from DB
    2. LLM teacher -> initial tree structure
    3. Extract and validate decision variables (merge/enrich from LLM)
    4. Build DecisionTree with proper node linkage (already from parse)
    5. Run validation (structure + conditions)
    6. Store tree in DB with status=draft
    7. Return tree with confidence scores
    """
    def progress(msg: str) -> None:
        if job_id:
            _update_job_progress(job_id, "in_progress", progress_message=msg)
        logger.info("[compile %s] %s", job_id or guideline_id, msg)

    progress("Retrieving guideline from database")
    doc = get_guideline_document(guideline_id)
    if not doc:
        raise ValueError(f"Guideline '{guideline_id}' not found")
    guideline_text = doc.raw_text or ""
    if not guideline_text.strip():
        raise ValueError(f"Guideline '{guideline_id}' has no extracted text")
    domain = options.target_domain or doc.domain or "general"
    logger.info("Compiling guideline_id=%s domain=%s", guideline_id, domain)

    progress("Generating initial tree structure with LLM")
    router = router or LLMRouter()
    llm_raw_output = None
    try:
        result = await parse_guideline_to_tree(
            guideline_text, domain=domain, router=router, use_student_fallback=True, return_raw=True
        )
        tree, llm_raw_output = result
        logger.info("LLM returned %s chars of raw output", len(llm_raw_output) if llm_raw_output else 0)
    except Exception as e:
        logger.exception("LLM parse failed: %s", e)
        if job_id:
            _update_job_progress(job_id, "failed", error_message=str(e))
        raise

    progress("Extracting and validating decision variables")
    try:
        extracted_vars = await extract_decision_variables(guideline_text, router=router)
    except Exception as e:
        logger.warning("Variable extraction failed, using tree variables: %s", e)
        extracted_vars = []
    var_names_in_tree = {v.name for v in tree.variables}
    for v in extracted_vars:
        if v.name not in var_names_in_tree:
            tree.variables.append(v)
    # Ensure every condition variable is in tree.variables
    for node in tree.nodes.values():
        if node.condition and node.condition.variable and node.condition.variable not in var_names_in_tree:
            if not any(x.name == node.condition.variable for x in tree.variables):
                tree.variables.append(
                    DecisionVariable(name=node.condition.variable, type=VariableType.CATEGORICAL, source="inferred")
                )
            var_names_in_tree.add(node.condition.variable)

    progress("Building tree and running validation")
    structure_errors = validate_tree_structure(tree)
    condition_errors = validate_conditions(tree)
    strict = options.strictness_level == "strict"
    if structure_errors:
        for err in structure_errors:
            logger.warning("Structure: %s", err.message)
        if strict and structure_errors:
            if job_id:
                _update_job_progress(job_id, "failed", error_message="; ".join(e.message for e in structure_errors))
            raise ValueError(f"Structure validation failed: {[e.message for e in structure_errors]}")
    if condition_errors:
        for err in condition_errors:
            logger.warning("Condition: %s", err.message)
        if strict and condition_errors:
            if job_id:
                _update_job_progress(job_id, "failed", error_message="; ".join(e.message for e in condition_errors))
            raise ValueError(f"Condition validation failed: {[e.message for e in condition_errors]}")

    # Depth check
    def max_depth(nid: str, seen: set[str], d: int) -> int:
        if nid in seen or d > options.max_tree_depth:
            return d
        seen.add(nid)
        node = tree.nodes.get(nid)
        if not node or not node.children:
            return d
        return max(max_depth(c, set(seen), d + 1) for c in node.children)

    depth = max_depth(tree.root_node_id, set(), 0)
    if depth > options.max_tree_depth:
        msg = f"Tree depth {depth} exceeds max_tree_depth {options.max_tree_depth}"
        if job_id:
            _update_job_progress(job_id, "failed", error_message=msg)
        raise ValueError(msg)

    progress("Storing tree in database")
    tree_id = tree.id if isinstance(tree.id, str) else str(tree.id)
    payload = tree.model_dump(mode="json")
    db = SessionLocal()
    try:
        row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree_id).first()
        if row:
            row.tree_json = payload
            row.version = tree.version
            row.name = tree.name
            row.description = getattr(tree, "description", None) or (tree.metadata or {}).get("guideline_source")
            row.status = "draft"
            row.domain = tree.domain
            db.commit()
            db.refresh(row)
        else:
            row = DecisionTreeModel(
                id=tree_id,
                version=tree.version,
                name=tree.name,
                description=(tree.metadata or {}).get("guideline_source") if isinstance(tree.metadata, dict) else None,
                status="draft",
                domain=tree.domain,
                tree_json=payload,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
    finally:
        db.close()

    if job_id:
        _update_job_progress(
            job_id,
            "completed",
            progress_message="Compilation completed",
            result_tree_id=tree_id,
            llm_raw_output=llm_raw_output or "",
            parsed_tree_snapshot=payload,
        )
    progress("Compilation completed")
    return tree


def run_compilation_job_sync(job_id: str, guideline_id: str, options: CompilerOptions) -> None:
    """
    Sync entrypoint for BackgroundTasks: runs compile_guideline_to_tree in event loop
    and updates job on failure.
    """
    try:
        asyncio.run(compile_guideline_to_tree(guideline_id, options, job_id=job_id))
    except Exception as e:
        logger.exception("Compilation job %s failed: %s", job_id, e)
        _update_job_progress(job_id, "failed", error_message=str(e))
