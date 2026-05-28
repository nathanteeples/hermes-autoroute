"""Configuration loading for Hermes Autoroute."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .types import EndpointConfig


DEFAULT_PORT = 8765


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def data_dir() -> Path:
    path = Path(os.environ.get("HERMES_AUTOROUTE_DATA_DIR", hermes_home() / "autoroute"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return Path(os.environ.get("HERMES_AUTOROUTE_CONFIG", data_dir() / "config.json")).expanduser()


def state_path() -> Path:
    return Path(os.environ.get("HERMES_AUTOROUTE_STATE", data_dir() / "state.json")).expanduser()


def default_config() -> dict[str, Any]:
    return {
        "router": {
            "host": "127.0.0.1",
            "port": DEFAULT_PORT,
            "background_on_session_start": True,
        },
        "catalog": {
            "openrouter_enabled": True,
            "litellm_enabled": True,
            "ttl_seconds": 86400,
        },
        "probe": {
            "enabled": True,
            "timeout_seconds": 20,
            "max_models_per_run": 100,
            "circuit_breaker_seconds": 600,
        },
        "routing": {
            "default_mode": "balanced",
            "max_attempts": 3,
            "allow_paid_escalation": True,
            "weights": {
                "quality": 0.42,
                "cost": 0.22,
                "latency": 0.16,
                "reliability": 0.20,
            },
        },
        "endpoints": [],
    }


def ensure_config_file() -> Path:
    path = config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default_config(), indent=2) + "\n", encoding="utf-8")
    return path


def load_config() -> dict[str, Any]:
    ensure_config_file()
    with config_path().open("r", encoding="utf-8") as fh:
        loaded = json.load(fh)
    return _deep_merge(default_config(), loaded)


def save_config(config: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def endpoints_from_config(config: dict[str, Any] | None = None) -> list[EndpointConfig]:
    config = config or load_config()
    endpoints: list[EndpointConfig] = []
    for item in config.get("endpoints", []):
        if not item.get("enabled", True):
            continue
        endpoints.append(
            EndpointConfig(
                name=item["name"],
                base_url=item["base_url"],
                api_key_env=item.get("api_key_env"),
                api_key_file=item.get("api_key_file"),
                enabled=item.get("enabled", True),
                headers=dict(item.get("headers", {})),
                timeout_seconds=float(item.get("timeout_seconds", 30.0)),
            )
        )
    return endpoints


def router_address(config: dict[str, Any] | None = None) -> tuple[str, int]:
    config = config or load_config()
    router = config.get("router", {})
    return str(router.get("host", "127.0.0.1")), int(router.get("port", DEFAULT_PORT))


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
