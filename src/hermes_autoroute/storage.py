"""JSON-backed state store.

The first version deliberately uses a single JSON file. It is easy to inspect,
portable across Hermes installs, and good enough for model catalogs/health
state. A future version can swap this for sqlite without changing callers.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from time import time
from typing import Any

from .config import state_path
from .types import HealthRecord, ModelRecord


class StateStore:
    def __init__(self, path: Path | None = None):
        self.path = path or state_path()
        self.data: dict[str, Any] = {
            "models": {},
            "health": {},
            "metadata": {},
            "decisions": [],
            "catalog_updated_at": None,
        }
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        for key, value in loaded.items():
            self.data[key] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def upsert_model(self, model: ModelRecord) -> None:
        existing = self.data["models"].get(model.key)
        record = asdict(model)
        if existing:
            record["first_seen_at"] = existing.get("first_seen_at", model.first_seen_at)
        record["last_seen_at"] = time()
        self.data["models"][model.key] = record

    def get_models(self) -> list[ModelRecord]:
        return [ModelRecord(**item) for item in self.data.get("models", {}).values()]

    def upsert_health(self, health: HealthRecord) -> None:
        self.data["health"][health.key] = asdict(health)

    def get_health(self, key: str) -> HealthRecord | None:
        item = self.data.get("health", {}).get(key)
        return HealthRecord(**item) if item else None

    def get_all_health(self) -> dict[str, HealthRecord]:
        return {key: HealthRecord(**value) for key, value in self.data.get("health", {}).items()}

    def upsert_metadata(self, canonical_id: str, metadata: dict[str, Any]) -> None:
        self.data["metadata"][canonical_id] = metadata
        self.data["catalog_updated_at"] = time()

    def get_metadata(self, canonical_id: str) -> dict[str, Any] | None:
        return self.data.get("metadata", {}).get(canonical_id)

    def add_decision(self, decision: dict[str, Any]) -> None:
        decisions = self.data.setdefault("decisions", [])
        decisions.append(decision)
        del decisions[:-100]

    def last_decision(self) -> dict[str, Any] | None:
        decisions = self.data.get("decisions", [])
        return decisions[-1] if decisions else None

