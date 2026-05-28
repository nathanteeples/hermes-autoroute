"""Endpoint inventory scanning."""

from __future__ import annotations

from .catalog import enrich_model
from .config import endpoints_from_config
from .http import endpoint_headers, get_json
from .storage import StateStore
from .types import ModelRecord


def scan_models(store: StateStore | None = None) -> list[ModelRecord]:
    store = store or StateStore()
    found: list[ModelRecord] = []
    for endpoint in endpoints_from_config():
        payload = get_json(
            endpoint.models_url,
            headers=endpoint_headers(endpoint),
            timeout=endpoint.timeout_seconds,
        )
        for item in payload.get("data", []):
            model_id = item.get("id") if isinstance(item, dict) else None
            if not model_id:
                continue
            record = ModelRecord(endpoint=endpoint.name, model=model_id)
            enrich_model(record, store)
            store.upsert_model(record)
            found.append(record)
    store.save()
    return found

