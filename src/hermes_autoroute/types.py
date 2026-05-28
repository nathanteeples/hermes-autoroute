"""Shared datatypes for discovery, routing, and persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any


@dataclass(slots=True)
class EndpointConfig:
    name: str
    base_url: str
    api_key_env: str | None = None
    api_key_file: str | None = None
    enabled: bool = True
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 30.0

    @property
    def models_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/models"

    @property
    def chat_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"


@dataclass(slots=True)
class ModelRecord:
    endpoint: str
    model: str
    canonical_id: str | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None
    input_cost_per_mtok: float | None = None
    output_cost_per_mtok: float | None = None
    supports_tools: bool | None = None
    supports_structured_output: bool | None = None
    supports_vision: bool | None = None
    supports_reasoning: bool | None = None
    quality_tier: float | None = None
    first_seen_at: float = field(default_factory=time)
    last_seen_at: float = field(default_factory=time)

    @property
    def key(self) -> str:
        return f"{self.endpoint}:{self.model}"


@dataclass(slots=True)
class HealthRecord:
    endpoint: str
    model: str
    status: str = "unknown"
    last_probe_at: float | None = None
    avg_latency_ms: float | None = None
    success_count: int = 0
    failure_count: int = 0
    last_error: str | None = None
    circuit_open_until: float | None = None

    @property
    def key(self) -> str:
        return f"{self.endpoint}:{self.model}"

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total else 0.0


@dataclass(slots=True)
class RouteScore:
    endpoint: str
    model: str
    score: float
    reasons: list[str]


@dataclass(slots=True)
class PromptFeatures:
    prompt_tokens_estimate: int
    task_class: str
    complexity: float
    importance: float
    needs_json: bool
    needs_tools: bool
    needs_vision: bool
    latency_sensitive: bool
    cost_sensitive: bool


JsonDict = dict[str, Any]
