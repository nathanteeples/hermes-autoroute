"""Hermes plugin command helpers."""

from __future__ import annotations

import json
from threading import Lock

from .config import load_config
from .server import serve_in_thread
from .storage import StateStore

_START_LOCK = Lock()
_STARTED = False


def start_background_router() -> None:
    global _STARTED
    config = load_config()
    if not config.get("router", {}).get("background_on_session_start", True):
        return
    with _START_LOCK:
        if _STARTED:
            return
        try:
            serve_in_thread()
            _STARTED = True
        except OSError:
            # The configured port is probably already served by a foreground
            # `hermes autoroute serve`; that is fine.
            _STARTED = True


def slash_status(raw_args: str = "") -> str:
    store = StateStore()
    if raw_args.strip() == "explain":
        return json.dumps(store.last_decision() or {"message": "No routing decision recorded yet"}, indent=2)
    models = store.get_models()
    health = store.get_all_health()
    healthy = sum(1 for item in health.values() if item.status == "healthy")
    return (
        f"Autoroute: {len(models)} discovered models, {healthy} healthy. "
        "Run `/autoroute explain` for the latest routing decision."
    )

