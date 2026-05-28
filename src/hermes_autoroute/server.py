"""OpenAI-compatible local router server."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

from .config import load_config, router_address
from .router import AutorouteRouter, RoutingError
from .storage import StateStore


class AutorouteServer(ThreadingHTTPServer):
    daemon_threads = True


class AutorouteHandler(BaseHTTPRequestHandler):
    server_version = "HermesAutoroute/0.1"

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/v1/models":
            self._json(
                {
                    "object": "list",
                    "data": [
                        {"id": "auto", "object": "model", "owned_by": "hermes-autoroute"},
                        {"id": "auto/tiny", "object": "model", "owned_by": "hermes-autoroute"},
                        {"id": "auto/standard", "object": "model", "owned_by": "hermes-autoroute"},
                        {"id": "auto/reasoning", "object": "model", "owned_by": "hermes-autoroute"},
                        {"id": "auto/critical", "object": "model", "owned_by": "hermes-autoroute"},
                    ],
                }
            )
            return
        if self.path.rstrip("/") == "/health":
            self._json({"ok": True})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/chat/completions":
            self.send_error(404)
            return
        try:
            payload = self._read_json()
            status, headers, body = AutorouteRouter(StateStore()).complete_raw(payload)
            self.send_response(status)
            self.send_header("Content-Type", headers.get("Content-Type", "application/json"))
            for name in ("X-Hermes-Autoroute-Endpoint", "X-Hermes-Autoroute-Model"):
                if name in headers:
                    self.send_header(name, headers[name])
            self.end_headers()
            self.wfile.write(body)
        except RoutingError as exc:
            self._json({"error": {"message": str(exc), "type": "autoroute_routing_error"}}, status=503)
        except Exception as exc:
            self._json({"error": {"message": str(exc), "type": "autoroute_error"}}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_forever(host: str | None = None, port: int | None = None) -> None:
    config = load_config()
    cfg_host, cfg_port = router_address(config)
    server = AutorouteServer((host or cfg_host, port or cfg_port), AutorouteHandler)
    print(f"Hermes Autoroute serving OpenAI-compatible API at http://{server.server_address[0]}:{server.server_address[1]}/v1")
    server.serve_forever()


def serve_in_thread(host: str | None = None, port: int | None = None) -> Thread:
    config = load_config()
    cfg_host, cfg_port = router_address(config)
    server = AutorouteServer((host or cfg_host, port or cfg_port), AutorouteHandler)
    thread = Thread(target=server.serve_forever, name="hermes-autoroute", daemon=True)
    thread.start()
    return thread

