"""Model metadata enrichment from public catalogs."""

from __future__ import annotations

from typing import Any

from .http import get_json
from .storage import StateStore


OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
LITELLM_PRICES_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)


def refresh_catalog(store: StateStore | None = None, *, timeout: float = 20.0) -> int:
    store = store or StateStore()
    count = 0
    count += _refresh_openrouter(store, timeout)
    count += _refresh_litellm(store, timeout)
    store.save()
    return count


def enrich_model(record, store: StateStore) -> None:
    candidates = _candidate_ids(record.model)
    for candidate in candidates:
        metadata = store.get_metadata(candidate)
        if metadata:
            _apply_metadata(record, metadata)
            record.canonical_id = candidate
            return
    record.canonical_id = record.model


def _refresh_openrouter(store: StateStore, timeout: float) -> int:
    try:
        payload = get_json(OPENROUTER_MODELS_URL, timeout=timeout)
    except Exception:
        return 0
    count = 0
    for item in payload.get("data", []):
        model_id = item.get("id")
        if not model_id:
            continue
        pricing = item.get("pricing") or {}
        metadata = {
            "source": "openrouter",
            "id": model_id,
            "context_window": _as_int(item.get("context_length")),
            "max_output_tokens": _as_int(item.get("top_provider", {}).get("max_completion_tokens")),
            "input_cost_per_mtok": _price_per_mtok(pricing.get("prompt")),
            "output_cost_per_mtok": _price_per_mtok(pricing.get("completion")),
            "supports_tools": "tools" in item.get("supported_parameters", []),
            "supports_structured_output": "response_format" in item.get("supported_parameters", []),
            "supports_vision": _has_modality(item, "image"),
            "supports_reasoning": "reasoning" in item.get("supported_parameters", []),
            "quality_tier": _quality_guess(model_id),
        }
        store.upsert_metadata(model_id, metadata)
        count += 1
    return count


def _refresh_litellm(store: StateStore, timeout: float) -> int:
    try:
        payload = get_json(LITELLM_PRICES_URL, timeout=timeout)
    except Exception:
        return 0
    count = 0
    for model_id, item in payload.items():
        if not isinstance(item, dict):
            continue
        metadata = {
            "source": "litellm",
            "id": model_id,
            "context_window": _as_int(item.get("max_input_tokens") or item.get("max_tokens")),
            "max_output_tokens": _as_int(item.get("max_output_tokens")),
            "input_cost_per_mtok": _price_per_mtok(item.get("input_cost_per_token")),
            "output_cost_per_mtok": _price_per_mtok(item.get("output_cost_per_token")),
            "supports_tools": item.get("supports_function_calling"),
            "supports_structured_output": item.get("supports_response_schema"),
            "supports_vision": item.get("mode") == "image_generation" or item.get("supports_vision"),
            "supports_reasoning": _looks_reasoning(model_id),
            "quality_tier": _quality_guess(model_id),
        }
        store.upsert_metadata(model_id, metadata)
        count += 1
    return count


def _apply_metadata(record, metadata: dict[str, Any]) -> None:
    record.context_window = metadata.get("context_window") or record.context_window
    record.max_output_tokens = metadata.get("max_output_tokens") or record.max_output_tokens
    record.input_cost_per_mtok = metadata.get("input_cost_per_mtok")
    record.output_cost_per_mtok = metadata.get("output_cost_per_mtok")
    record.supports_tools = metadata.get("supports_tools")
    record.supports_structured_output = metadata.get("supports_structured_output")
    record.supports_vision = metadata.get("supports_vision")
    record.supports_reasoning = metadata.get("supports_reasoning")
    record.quality_tier = metadata.get("quality_tier")


def _candidate_ids(model_id: str) -> list[str]:
    parts = [model_id]
    if "/" in model_id:
        parts.append(model_id.split("/", 1)[1])
    return list(dict.fromkeys(parts))


def _price_per_mtok(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0.001:
        return number * 1_000_000
    return number


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _has_modality(item: dict[str, Any], name: str) -> bool:
    architecture = item.get("architecture") or {}
    modalities = architecture.get("input_modalities") or []
    return name in modalities


def _looks_reasoning(model_id: str) -> bool:
    lowered = model_id.lower()
    return any(token in lowered for token in ("reason", "thinking", "/o1", "/o3", "/o4", "r1"))


def _quality_guess(model_id: str) -> float:
    lowered = model_id.lower()
    if any(token in lowered for token in ("opus", "gpt-5", "o3", "gemini-3", "sonnet-4", "r1")):
        return 0.95
    if any(token in lowered for token in ("sonnet", "gpt-4", "gemini-2.5", "deepseek", "qwen3")):
        return 0.82
    if any(token in lowered for token in ("haiku", "mini", "flash", "lite", "small", "8b")):
        return 0.48
    return 0.65

