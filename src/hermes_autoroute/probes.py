"""Model health and capability probes."""

from __future__ import annotations

from time import perf_counter, time

from .config import endpoints_from_config, load_config
from .http import endpoint_headers, post_json
from .storage import StateStore
from .types import HealthRecord


def probe_models(store: StateStore | None = None) -> dict[str, HealthRecord]:
    store = store or StateStore()
    config = load_config()
    probe_cfg = config.get("probe", {})
    max_models = int(probe_cfg.get("max_models_per_run", 100))
    timeout = float(probe_cfg.get("timeout_seconds", 20.0))
    endpoints = {endpoint.name: endpoint for endpoint in endpoints_from_config(config)}
    results: dict[str, HealthRecord] = {}

    for model in store.get_models()[:max_models]:
        endpoint = endpoints.get(model.endpoint)
        if not endpoint:
            continue
        health = store.get_health(model.key) or HealthRecord(endpoint=model.endpoint, model=model.model)
        started = perf_counter()
        try:
            post_json(
                endpoint.chat_url,
                {
                    "model": model.model,
                    "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
                    "temperature": 0,
                    "max_tokens": 8,
                },
                headers=endpoint_headers(endpoint),
                timeout=timeout,
            )
            latency_ms = (perf_counter() - started) * 1000
            health.status = "healthy"
            health.last_probe_at = time()
            health.avg_latency_ms = _rolling_average(health.avg_latency_ms, latency_ms)
            health.success_count += 1
            health.last_error = None
            health.circuit_open_until = None
        except Exception as exc:
            health.status = "failing"
            health.last_probe_at = time()
            health.failure_count += 1
            health.last_error = str(exc)[:500]
            health.circuit_open_until = time() + float(probe_cfg.get("circuit_breaker_seconds", 600))
        store.upsert_health(health)
        results[model.key] = health

    store.save()
    return results


def _rolling_average(current: float | None, new_value: float, alpha: float = 0.25) -> float:
    if current is None:
        return new_value
    return current * (1.0 - alpha) + new_value * alpha

