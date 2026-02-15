"""
Flexible LLM integration layer with cost-efficient teacher/student routing.

- Teacher model: high-stakes guideline parsing (GPT-4 / Claude Opus).
- Student model: cheaper iterative edits (GPT-4 mini / Claude Haiku).
- Configuration via environment variables; providers swappable via strategy pattern.

Environment variables:
  OPENAI_API_KEY, ANTHROPIC_API_KEY     API keys (set one for the provider you use)
  CAIRE_LLM_PROVIDER                    "openai" | "anthropic" (default: openai)
  CAIRE_LLM_TEACHER_MODEL               e.g. gpt-4o, claude-sonnet-4-20250514
  CAIRE_LLM_STUDENT_MODEL               e.g. gpt-4o-mini, claude-3-5-haiku-20241022
  CAIRE_LLM_TEACHER_PROVIDER            override provider for teacher (default: CAIRE_LLM_PROVIDER)
  CAIRE_LLM_STUDENT_PROVIDER            override provider for student

Optional deps: pip install openai anthropic  (or use project's [llm] extra)
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional, Protocol

from backend.models.decision_tree import (
    DecisionNode,
    DecisionTree,
    DecisionVariable,
    NodeType,
    VariableType,
)
from backend.models_db import LLMCallLog
from backend.database import SessionLocal

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Configuration (environment variables)
# -----------------------------------------------------------------------------

def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(key, default)

OPENAI_API_KEY = _env("OPENAI_API_KEY")
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")

# Provider: "openai" or "anthropic"
CAIRE_LLM_PROVIDER = _env("CAIRE_LLM_PROVIDER", "openai").lower()

# Teacher: high-quality for parsing (e.g. gpt-4o, claude-3-5-sonnet)
CAIRE_LLM_TEACHER_MODEL = _env("CAIRE_LLM_TEACHER_MODEL") or (
    "gpt-4o" if CAIRE_LLM_PROVIDER == "openai" else "claude-sonnet-4-20250514"
)
# Student: cheaper for refinements (e.g. gpt-4o-mini, claude-3-5-haiku)
CAIRE_LLM_STUDENT_MODEL = _env("CAIRE_LLM_STUDENT_MODEL") or (
    "gpt-4o-mini" if CAIRE_LLM_PROVIDER == "openai" else "claude-3-5-haiku-20241022"
)

# Optional overrides per role (e.g. use different provider for student)
CAIRE_LLM_TEACHER_PROVIDER = _env("CAIRE_LLM_TEACHER_PROVIDER", CAIRE_LLM_PROVIDER).lower()
CAIRE_LLM_STUDENT_PROVIDER = _env("CAIRE_LLM_STUDENT_PROVIDER", CAIRE_LLM_PROVIDER).lower()

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# -----------------------------------------------------------------------------
# Usage / cost estimation (rough $ per 1M tokens)
# -----------------------------------------------------------------------------

COST_PER_MILLION = {
    ("openai", "gpt-4o"): (2.50, 10.00),
    ("openai", "gpt-4o-mini"): (0.15, 0.60),
    ("anthropic", "claude-sonnet-4-20250514"): (3.00, 15.00),
    ("anthropic", "claude-3-5-haiku-20241022"): (0.80, 4.00),
}


def _estimate_cost_usd(provider: str, model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    key = (provider, model)
    if key not in COST_PER_MILLION:
        # Generic fallback
        for (p, m), (in_p, out_p) in COST_PER_MILLION.items():
            if p == provider:
                in_p, out_p = in_p, out_p
                return (input_tokens / 1_000_000) * in_p + (output_tokens / 1_000_000) * out_p
        return None
    in_p, out_p = COST_PER_MILLION[key]
    return (input_tokens / 1_000_000) * in_p + (output_tokens / 1_000_000) * out_p


# -----------------------------------------------------------------------------
# Provider protocol and implementations
# -----------------------------------------------------------------------------


class LLMUsage:
    """Token usage and cost for one call."""

    __slots__ = ("input_tokens", "output_tokens", "model", "provider", "estimated_cost_usd")

    def __init__(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str = "",
        provider: str = "",
        estimated_cost_usd: Optional[float] = None,
    ):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.model = model
        self.provider = provider
        self.estimated_cost_usd = estimated_cost_usd or _estimate_cost_usd(
            provider, model, input_tokens, output_tokens
        )


class LLMProvider(Protocol):
    """Strategy interface for LLM providers."""

    async def call(self, prompt: str, system_prompt: str, model: str) -> tuple[str, LLMUsage]:
        """Return (content, usage)."""
        ...


class OpenAIProvider:
    """OpenAI API (async)."""

    def __init__(self, api_key: Optional[str] = None):
        self._key = api_key or OPENAI_API_KEY
        self._client = None

    def _client_or_raise(self):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeError("OpenAI provider requires: pip install openai")
        if not self._key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._key)
        return self._client

    async def call(self, prompt: str, system_prompt: str, model: str) -> tuple[str, LLMUsage]:
        client = self._client_or_raise()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        usage = response.usage
        input_tokens = getattr(usage, "input_tokens", usage.prompt_tokens)
        output_tokens = getattr(usage, "output_tokens", usage.completion_tokens)
        u = LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            provider="openai",
        )
        return content, u


class AnthropicProvider:
    """Anthropic API (async)."""

    def __init__(self, api_key: Optional[str] = None):
        self._key = api_key or ANTHROPIC_API_KEY
        self._client = None

    def _client_or_raise(self):
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise RuntimeError("Anthropic provider requires: pip install anthropic")
        if not self._key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self._key)
        return self._client

    async def call(self, prompt: str, system_prompt: str, model: str) -> tuple[str, LLMUsage]:
        client = self._client_or_raise()
        response = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = (response.content[0].text if response.content else "").strip()
        usage = response.usage
        u = LLMUsage(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model=model,
            provider="anthropic",
        )
        return content, u


def _get_provider(name: str) -> LLMProvider:
    if name == "openai":
        return OpenAIProvider()
    if name == "anthropic":
        return AnthropicProvider()
    raise ValueError(f"Unknown LLM provider: {name}")


# -----------------------------------------------------------------------------
# Retry with exponential backoff
# -----------------------------------------------------------------------------


async def _retry_async(
    fn,
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    **kwargs,
):
    last_error = None
    for attempt in range(max_attempts):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning("LLM call failed (attempt %s/%s), retrying in %.1fs: %s", attempt + 1, max_attempts, delay, e)
                await asyncio.sleep(delay)
    raise last_error


# -----------------------------------------------------------------------------
# Cost logging to SQLite
# -----------------------------------------------------------------------------


def _log_usage(role: str, usage: LLMUsage) -> None:
    try:
        db = SessionLocal()
        try:
            log = LLMCallLog(
                provider=usage.provider,
                model=usage.model,
                role=role,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                estimated_cost_usd=usage.estimated_cost_usd,
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning("Failed to log LLM usage to DB: %s", e)


# -----------------------------------------------------------------------------
# LLM Router
# -----------------------------------------------------------------------------


class LLMRouter:
    """
    Routes requests to teacher (high-quality) or student (cost-efficient) models.
    Configuration via environment variables; providers swappable.
    """

    def __init__(
        self,
        teacher_provider: Optional[str] = None,
        student_provider: Optional[str] = None,
        teacher_model: Optional[str] = None,
        student_model: Optional[str] = None,
    ):
        self.teacher_provider_name = teacher_provider or CAIRE_LLM_TEACHER_PROVIDER
        self.student_provider_name = student_provider or CAIRE_LLM_STUDENT_PROVIDER
        self.teacher_model = teacher_model or CAIRE_LLM_TEACHER_MODEL
        self.student_model = student_model or CAIRE_LLM_STUDENT_MODEL
        self._teacher: Optional[LLMProvider] = None
        self._student: Optional[LLMProvider] = None

    def _get_teacher(self) -> LLMProvider:
        if self._teacher is None:
            self._teacher = _get_provider(self.teacher_provider_name)
        return self._teacher

    def _get_student(self) -> LLMProvider:
        if self._student is None:
            self._student = _get_provider(self.student_provider_name)
        return self._student

    async def call_teacher_model(self, prompt: str, system_prompt: str) -> tuple[str, LLMUsage]:
        """High-stakes guideline parsing: use teacher model with retry and logging."""
        provider = self._get_teacher()

        async def _call():
            return await provider.call(prompt, system_prompt, self.teacher_model)

        content, usage = await _retry_async(_call)
        _log_usage("teacher", usage)
        logger.info(
            "Teacher call: %s %s, in=%s out=%s cost≈$%s",
            usage.provider, self.teacher_model,
            usage.input_tokens, usage.output_tokens,
            f"{usage.estimated_cost_usd:.4f}" if usage.estimated_cost_usd else "?",
        )
        return content, usage

    async def call_student_model(self, prompt: str, system_prompt: str) -> tuple[str, LLMUsage]:
        """Cheaper iterative edits: use student model with retry and logging."""
        provider = self._get_student()

        async def _call():
            return await provider.call(prompt, system_prompt, self.student_model)

        content, usage = await _retry_async(_call)
        _log_usage("student", usage)
        logger.info(
            "Student call: %s %s, in=%s out=%s cost≈$%s",
            usage.provider, self.student_model,
            usage.input_tokens, usage.output_tokens,
            f"{usage.estimated_cost_usd:.4f}" if usage.estimated_cost_usd else "?",
        )
        return content, usage


# -----------------------------------------------------------------------------
# JSON extraction from LLM output (strip markdown, find JSON object)
# -----------------------------------------------------------------------------


def _extract_json_from_response(text: str) -> dict[str, Any]:
    """Strip markdown code fences and extract first JSON object."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    for pattern in (r"```(?:json)?\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```"):
        m = re.search(pattern, text)
        if m:
            text = m.group(1).strip()
    # Find first { ... } or [ ... ]
    start = text.find("{")
    if start == -1:
        start = text.find("[")
    if start == -1:
        raise ValueError("No JSON object or array found in response")
    depth = 0
    end = -1
    open_c, close_c = ("{", "}") if text[start] == "{" else ("[", "]")
    for i in range(start, len(text)):
        if text[i] == open_c:
            depth += 1
        elif text[i] == close_c:
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        raise ValueError("Unclosed JSON in response")
    return json.loads(text[start : end + 1])


# -----------------------------------------------------------------------------
# Guideline parsing functions
# -----------------------------------------------------------------------------


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


async def parse_guideline_to_tree(
    guideline_text: str,
    domain: str,
    router: Optional[LLMRouter] = None,
    use_student_fallback: bool = True,
) -> DecisionTree:
    """
    Parse guideline text into an initial DecisionTree using the teacher model.
    Returns tree with confidence scores in each node's metadata.
    Falls back to student model if teacher fails when use_student_fallback=True.
    """
    router = router or LLMRouter()
    system_prompt = _load_prompt("guideline_parser_system.txt")
    example = _load_prompt("tree_structure.json")
    if example:
        system_prompt += "\n\n## Example output structure\n" + example

    user_prompt = f"Domain: {domain}\n\nGuideline text:\n\n{guideline_text[:12000]}"
    if len(guideline_text) > 12000:
        user_prompt += "\n\n[... text truncated ...]"

    content = None
    usage = None

    try:
        content, usage = await router.call_teacher_model(user_prompt, system_prompt)
    except Exception as e:
        if use_student_fallback:
            logger.warning("Teacher model failed, falling back to student: %s", e)
            try:
                content, usage = await router.call_student_model(user_prompt, system_prompt)
            except Exception as e2:
                raise RuntimeError(f"Both teacher and student model failed. Last error: {e2}") from e2
        else:
            raise

    raw = _extract_json_from_response(content)

    # Ensure nodes is dict (schema expects node_id -> node)
    nodes_data = raw.get("nodes")
    if isinstance(nodes_data, list):
        nodes_dict = {n["id"]: n for n in nodes_data if isinstance(n, dict) and "id" in n}
    else:
        nodes_dict = nodes_data or {}

    # Ensure each node has metadata with confidence if not present
    for nid, node in nodes_dict.items():
        if isinstance(node, dict):
            meta = node.get("metadata") or {}
            if not isinstance(meta, dict):
                meta = {}
            if "confidence" not in meta:
                meta["confidence"] = 0.8
            node["metadata"] = meta

    raw["nodes"] = nodes_dict
    raw.setdefault("domain", domain)
    raw.setdefault("version", "1.0.0")
    raw.setdefault("id", f"parsed-{domain}-v1")

    try:
        tree = DecisionTree.model_validate(raw)
    except Exception as e:
        raise ValueError(f"LLM output did not validate as DecisionTree: {e}") from e

    return tree


async def extract_decision_variables(
    guideline_text: str,
    router: Optional[LLMRouter] = None,
) -> list[DecisionVariable]:
    """
    Identify clinical variables, thresholds, and operators from guideline text.
    Maps to standard terminologies where possible.
    """
    router = router or LLMRouter()
    system_prompt = """You are a clinical data analyst. Extract all decision-relevant variables from the guideline text.
Output a JSON array only. Each element: {"name": "snake_case", "type": "numeric"|"boolean"|"categorical", "units": optional, "source": e.g. "patient_history"|"vital_signs"|"lab", "description": optional, "terminology_mapping": optional {"SNOMED": "...", "LOINC": "..."}}.
No markdown, no explanation."""
    user_prompt = f"Guideline text:\n\n{guideline_text[:8000]}"

    content, _ = await router.call_teacher_model(user_prompt, system_prompt)
    raw = _extract_json_from_response(content)
    if isinstance(raw, dict) and "variables" in raw:
        raw = raw["variables"]
    if not isinstance(raw, list):
        raw = [raw] if isinstance(raw, dict) else []

    variables = []
    for v in raw:
        if not isinstance(v, dict) or "name" not in v:
            continue
        try:
            v.setdefault("type", "categorical")
            if isinstance(v["type"], str) and v["type"] not in ("numeric", "boolean", "categorical"):
                v["type"] = "categorical"
            variables.append(DecisionVariable.model_validate(v))
        except Exception:
            continue
    return variables


async def refine_node(
    node: DecisionNode,
    instruction: str,
    router: Optional[LLMRouter] = None,
) -> DecisionNode:
    """
    Use the student model to apply a small edit to a node (e.g. "make this condition more specific").
    """
    router = router or LLMRouter()
    system_prompt = _load_prompt("refinement_system.txt")
    user_prompt = f"Current node (JSON):\n{node.model_dump_json(indent=2)}\n\nInstruction: {instruction}"

    content, _ = await router.call_student_model(user_prompt, system_prompt)
    raw = _extract_json_from_response(content)
    if not isinstance(raw, dict):
        raise ValueError("Refinement response was not a JSON object")

    # Preserve id/type if not in response
    raw.setdefault("id", node.id)
    raw.setdefault("type", node.type.value if isinstance(node.type, NodeType) else node.type)
    try:
        return DecisionNode.model_validate(raw)
    except Exception as e:
        raise ValueError(f"Refinement output did not validate as DecisionNode: {e}") from e
