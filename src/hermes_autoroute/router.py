"""Core routing engine."""

from __future__ import annotations

import json
from time import perf_counter, time
from typing import Any

from .config import endpoints_from_config, load_config
from .http import HttpError, endpoint_headers, post_raw
from .scanner import scan_models
from .scoring import extract_prompt_features, score_candidate
from .storage import StateStore
from .types import HealthRecord, RouteScore


class RoutingError(RuntimeError):
    pass


class AutorouteRouter:
    def __init__(self, store: StateStore | None = None):
        self.store = store or StateStore()

    def complete_raw(self, payload: dict[str, Any]) -> tuple[int, dict[str, str], bytes]:
        config = load_config()
        attempts = int(config.get("routing", {}).get("max_attempts", 3))
        endpoint_by_name = {endpoint.name: endpoint for endpoint in endpoints_from_config(config)}
        candidates = self.rank(payload)
        if not candidates:
            try:
                scan_models(self.store)
            except Exception:
                pass
            candidates = self.rank(payload)
        if not candidates:
            raise RoutingError("No healthy compatible models are available")

        errors: list[str] = []
        for score in candidates[:attempts]:
            endpoint = endpoint_by_name.get(score.endpoint)
            if not endpoint:
                continue
            downstream_payload = dict(payload)
            downstream_payload["model"] = score.model
            started = perf_counter()
            try:
                status, headers, body = post_raw(
                    endpoint.chat_url,
                    downstream_payload,
                    headers=endpoint_headers(endpoint),
                    timeout=endpoint.timeout_seconds,
                )
                self._record_success(score, started, payload)
                headers = dict(headers)
                headers["X-Hermes-Autoroute-Endpoint"] = score.endpoint
                headers["X-Hermes-Autoroute-Model"] = score.model
                return status, headers, body
            except Exception as exc:
                errors.append(f"{score.endpoint}:{score.model}: {exc}")
                self._record_failure(score, exc)
        raise RoutingError("; ".join(errors) or "All routing attempts failed")

    def complete_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        _status, _headers, body = self.complete_raw(payload)
        return json.loads(body.decode("utf-8"))

    def rank(self, payload: dict[str, Any]) -> list[RouteScore]:
        config = load_config()
        features = extract_prompt_features(payload)
        weights = config.get("routing", {}).get("weights", {})
        health = self.store.get_all_health()
        scores: list[RouteScore] = []
        for model in self.store.get_models():
            score = score_candidate(model, health.get(model.key), features, weights)
            if score:
                scores.append(score)
        scores.sort(key=lambda item: item.score, reverse=True)
        return scores

    def _record_success(self, score: RouteScore, started: float, payload: dict[str, Any]) -> None:
        key = f"{score.endpoint}:{score.model}"
        health = self.store.get_health(key) or HealthRecord(endpoint=score.endpoint, model=score.model)
        latency_ms = (perf_counter() - started) * 1000
        health.status = "healthy"
        health.last_probe_at = time()
        health.success_count += 1
        health.avg_latency_ms = latency_ms if health.avg_latency_ms is None else health.avg_latency_ms * 0.8 + latency_ms * 0.2
        health.last_error = None
        health.circuit_open_until = None
        self.store.upsert_health(health)
        features = extract_prompt_features(payload)
        self.store.add_decision(
            {
                "at": time(),
                "endpoint": score.endpoint,
                "model": score.model,
                "score": score.score,
                "task_class": features.task_class,
                "prompt_tokens_estimate": features.prompt_tokens_estimate,
                "reasons": score.reasons,
            }
        )
        self.store.save()

    def _record_failure(self, score: RouteScore, exc: Exception) -> None:
        key = f"{score.endpoint}:{score.model}"
        config = load_config()
        breaker = float(config.get("probe", {}).get("circuit_breaker_seconds", 600))
        health = self.store.get_health(key) or HealthRecord(endpoint=score.endpoint, model=score.model)
        health.status = "failing"
        health.failure_count += 1
        health.last_error = str(exc)[:500]
        if isinstance(exc, HttpError) and exc.status in {401, 403}:
            health.circuit_open_until = time() + breaker * 6
        else:
            health.circuit_open_until = time() + breaker
        self.store.upsert_health(health)
        self.store.save()

