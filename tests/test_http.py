from hermes_autoroute.http import endpoint_headers
from hermes_autoroute.types import EndpointConfig


def test_endpoint_headers_reads_api_key_file(tmp_path):
    secret = tmp_path / "openrouter.key"
    secret.write_text("sk-test\n", encoding="utf-8")

    headers = endpoint_headers(
        EndpointConfig(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_file=str(secret),
        )
    )

    assert headers["Authorization"] == "Bearer sk-test"


def test_endpoint_headers_prefers_environment_key(monkeypatch, tmp_path):
    secret = tmp_path / "openrouter.key"
    secret.write_text("file-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")

    headers = endpoint_headers(
        EndpointConfig(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="OPENROUTER_API_KEY",
            api_key_file=str(secret),
        )
    )

    assert headers["Authorization"] == "Bearer env-key"

