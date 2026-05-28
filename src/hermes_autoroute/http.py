"""Small stdlib HTTP helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any

from .types import EndpointConfig


class HttpError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, body: bytes | None = None):
        super().__init__(message)
        self.status = status
        self.body = body or b""


def endpoint_headers(endpoint: EndpointConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json", **endpoint.headers}
    api_key = _api_key(endpoint)
    if api_key:
        headers.setdefault("Authorization", f"Bearer {api_key}")
    return headers


def _api_key(endpoint: EndpointConfig) -> str | None:
    if endpoint.api_key_env:
        api_key = os.environ.get(endpoint.api_key_env)
        if api_key:
            return api_key
    if endpoint.api_key_file:
        try:
            api_key = Path(endpoint.api_key_file).expanduser().read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return api_key or None
    return None


def get_json(url: str, headers: dict[str, str] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    return _json_request(request, timeout=timeout)


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers or {}, method="POST")
    return _json_request(request, timeout=timeout)


def post_raw(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers or {}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        raise HttpError(f"HTTP {exc.code}", status=exc.code, body=exc.read()) from exc
    except urllib.error.URLError as exc:
        raise HttpError(str(exc.reason)) from exc


def _json_request(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise HttpError(f"HTTP {exc.code}", status=exc.code, body=exc.read()) from exc
    except urllib.error.URLError as exc:
        raise HttpError(str(exc.reason)) from exc
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HttpError(f"Invalid JSON response: {exc}") from exc
