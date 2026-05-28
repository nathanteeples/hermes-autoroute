"""Provider registration shared by drop-in and pip plugin loading."""

from __future__ import annotations

import os


def register_autoroute_provider() -> bool:
    try:
        from providers import register_provider
        from providers.base import ProviderProfile
    except Exception:
        return False

    class AutorouteProfile(ProviderProfile):
        """Provider profile pointing Hermes at the local Autoroute proxy."""

        def fetch_models(self, *, api_key=None, timeout=8.0):
            return ["auto", "auto/tiny", "auto/standard", "auto/reasoning", "auto/critical"]

    register_provider(
        AutorouteProfile(
            name="autoroute",
            aliases=("auto", "hermes-autoroute"),
            api_mode="chat_completions",
            display_name="Hermes Autoroute",
            description="Local intelligent router across configured OpenAI-compatible endpoints",
            env_vars=("HERMES_AUTOROUTE_API_KEY", "HERMES_AUTOROUTE_BASE_URL"),
            base_url=os.environ.get("HERMES_AUTOROUTE_BASE_URL", "http://127.0.0.1:8765/v1"),
            auth_type="api_key",
            default_aux_model="auto/tiny",
            fallback_models=("auto/critical", "auto/reasoning", "auto/standard", "auto/tiny"),
        )
    )
    return True

