"""Command line interface for Hermes Autoroute."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .catalog import refresh_catalog
from .config import config_path, ensure_config_file
from .probes import probe_models
from .scanner import scan_models
from .server import serve_forever
from .storage import StateStore


def setup_argparse(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="autoroute_command")

    sub.add_parser("init-config", help="Create the default config file")
    sub.add_parser("scan", help="Scan configured endpoints for available models")
    sub.add_parser("catalog", help="Refresh public model metadata catalogs")
    sub.add_parser("probe", help="Probe discovered models for basic health")
    sub.add_parser("status", help="Show router inventory and health summary")
    sub.add_parser("models", help="List discovered downstream models")
    explain = sub.add_parser("explain", help="Explain a routing decision")
    explain.add_argument("--last", action="store_true", help="Show the latest recorded decision")
    serve = sub.add_parser("serve", help="Serve the local OpenAI-compatible router")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)


def run_from_args(args: argparse.Namespace) -> None:
    command = getattr(args, "autoroute_command", None)
    if command == "init-config":
        path = ensure_config_file()
        print(path)
    elif command == "catalog":
        count = refresh_catalog()
        print(f"Refreshed {count} catalog records")
    elif command == "scan":
        models = scan_models()
        print(f"Discovered {len(models)} models")
    elif command == "probe":
        results = probe_models()
        healthy = sum(1 for item in results.values() if item.status == "healthy")
        print(f"Probed {len(results)} models; {healthy} healthy")
    elif command == "status":
        _print_status()
    elif command == "models":
        _print_models()
    elif command == "explain":
        _print_json(StateStore().last_decision() or {"message": "No routing decision recorded yet"})
    elif command == "serve":
        serve_forever(host=getattr(args, "host", None), port=getattr(args, "port", None))
    else:
        print("Usage: hermes autoroute <init-config|catalog|scan|probe|status|models|explain|serve>")
        print(f"Config: {config_path()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes-autoroute")
    setup_argparse(parser)
    args = parser.parse_args(argv)
    run_from_args(args)
    return 0


def _print_status() -> None:
    store = StateStore()
    models = store.get_models()
    health = store.get_all_health()
    healthy = sum(1 for item in health.values() if item.status == "healthy")
    failing = sum(1 for item in health.values() if item.status == "failing")
    print(f"Config: {config_path()}")
    print(f"Models: {len(models)} discovered")
    print(f"Health: {healthy} healthy, {failing} failing, {max(0, len(models) - len(health))} unknown")
    last = store.last_decision()
    if last:
        print(f"Last route: {last['endpoint']}:{last['model']} ({last['task_class']}, score={last['score']:.3f})")


def _print_models() -> None:
    store = StateStore()
    health = store.get_all_health()
    for model in sorted(store.get_models(), key=lambda item: item.key):
        h = health.get(model.key)
        status = h.status if h else "unknown"
        cost = "?"
        if model.input_cost_per_mtok is not None or model.output_cost_per_mtok is not None:
            cost = f"{model.input_cost_per_mtok or 0:.2f}/{model.output_cost_per_mtok or 0:.2f}"
        print(f"{model.endpoint:16} {status:9} {model.model:50} ctx={model.context_window or '?':>7} cost={cost}")


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())

