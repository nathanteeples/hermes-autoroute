"""Prompt classification and candidate scoring."""

from __future__ import annotations

import json
import re
from time import time
from typing import Any

from .types import HealthRecord, ModelRecord, PromptFeatures, RouteScore


IMPORTANT_RE = re.compile(
    r"\b(production|deploy|security|auth|payment|delete|migration|legal|medical|financial|"
    r"customer|incident|outage|database|credentials|private key|secret)\b",
    re.I,
)
COMPLEX_RE = re.compile(
    r"\b(refactor|architecture|debug|investigate|prove|optimize|design|multi-step|"
    r"analyze|reason|plan|implement|integration)\b",
    re.I,
)


def extract_prompt_features(payload: dict[str, Any]) -> PromptFeatures:
    text = _messages_text(payload.get("messages", []))
    estimated_tokens = max(1, len(text) // 4)
    needs_json = bool(payload.get("response_format")) or "json" in text.lower()
    needs_tools = bool(payload.get("tools"))
    needs_vision = _contains_image(payload.get("messages", []))
    importance = min(1.0, 0.15 + 0.18 * len(IMPORTANT_RE.findall(text)))
    complexity = min(
        1.0,
        0.10
        + min(0.45, estimated_tokens / 16000)
        + 0.11 * len(COMPLEX_RE.findall(text))
        + (0.18 if needs_tools else 0)
        + (0.12 if needs_json else 0),
    )

    requested = str(payload.get("model") or "auto")
    task_class = _task_class(requested, complexity, importance, estimated_tokens, needs_vision)
    return PromptFeatures(
        prompt_tokens_estimate=estimated_tokens,
        task_class=task_class,
        complexity=complexity,
        importance=importance,
        needs_json=needs_json,
        needs_tools=needs_tools,
        needs_vision=needs_vision,
        latency_sensitive=estimated_tokens < 1500 and importance < 0.5,
        cost_sensitive=importance < 0.45 and task_class in {"tiny", "standard"},
    )


def score_candidate(
    model: ModelRecord,
    health: HealthRecord | None,
    features: PromptFeatures,
    weights: dict[str, float],
) -> RouteScore | None:
    now = time()
    if health and health.circuit_open_until and health.circuit_open_until > now:
        return None
    if health and health.status == "failing" and health.success_rate < 0.2:
        return None
    if features.needs_tools and model.supports_tools is False:
        return None
    if features.needs_json and model.supports_structured_output is False:
        return None
    if features.needs_vision and model.supports_vision is False:
        return None
    if model.context_window and model.context_window < features.prompt_tokens_estimate * 1.25:
        return None

    quality = _quality(model, features)
    cost = _cost_penalty(model)
    latency = _latency_penalty(health)
    reliability = _reliability(health)

    score = (
        weights.get("quality", 0.42) * quality
        - weights.get("cost", 0.22) * cost
        - weights.get("latency", 0.16) * latency
        + weights.get("reliability", 0.20) * reliability
    )

    reasons = [
        f"quality={quality:.2f}",
        f"cost_penalty={cost:.2f}",
        f"latency_penalty={latency:.2f}",
        f"reliability={reliability:.2f}",
    ]
    if features.task_class == "critical":
        score += quality * 0.25
        reasons.append("critical quality bonus")
    elif features.task_class == "tiny":
        score -= cost * 0.20
        reasons.append("tiny cost bias")
    return RouteScore(endpoint=model.endpoint, model=model.model, score=score, reasons=reasons)


def _task_class(requested: str, complexity: float, importance: float, tokens: int, needs_vision: bool) -> str:
    if requested.startswith("auto/"):
        return requested.split("/", 1)[1]
    if needs_vision:
        return "specialized"
    if importance >= 0.75:
        return "critical"
    if tokens > 32000:
        return "large_context"
    if complexity >= 0.68:
        return "reasoning"
    if complexity <= 0.25 and importance <= 0.35 and tokens < 4000:
        return "tiny"
    return "standard"


def _quality(model: ModelRecord, features: PromptFeatures) -> float:
    quality = model.quality_tier if model.quality_tier is not None else 0.62
    if features.task_class in {"reasoning", "critical"} and model.supports_reasoning:
        quality += 0.10
    if features.task_class == "tiny" and _looks_light(model.model):
        quality += 0.08
    return max(0.0, min(1.0, quality))


def _cost_penalty(model: ModelRecord) -> float:
    input_cost = model.input_cost_per_mtok
    output_cost = model.output_cost_per_mtok
    if input_cost is None and output_cost is None:
        return 0.35
    total = (input_cost or 0) + (output_cost or 0)
    return min(1.0, total / 50.0)


def _latency_penalty(health: HealthRecord | None) -> float:
    if not health or health.avg_latency_ms is None:
        return 0.35
    return min(1.0, health.avg_latency_ms / 12000.0)


def _reliability(health: HealthRecord | None) -> float:
    if not health:
        return 0.35
    if health.status == "healthy":
        return max(0.55, health.success_rate)
    if health.status == "degraded":
        return 0.45
    return 0.15


def _looks_light(model_id: str) -> bool:
    lowered = model_id.lower()
    return any(token in lowered for token in ("mini", "flash", "lite", "small", "haiku", "8b"))


def _messages_text(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        else:
            parts.append(json.dumps(content, ensure_ascii=False))
    return "\n".join(parts)


def _contains_image(messages: list[dict[str, Any]]) -> bool:
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") in {"image_url", "input_image"}:
                    return True
    return False

