#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PYTHON="${PYTHON:-python3}"
PROVIDER_DIR="$HERMES_HOME/plugins/model-providers/autoroute"
COMMAND_DIR="$HERMES_HOME/plugins/autoroute"
CONFIG_FILE="$HERMES_HOME/autoroute/config.json"
SECRETS_DIR="$HERMES_HOME/autoroute/secrets"

read_default() {
  local prompt="$1"
  local default="$2"
  local value
  read -r -p "$prompt [$default]: " value
  printf '%s' "${value:-$default}"
}

yes_no() {
  local prompt="$1"
  local default="${2:-Y}"
  local value
  local suffix="[y/N]"
  if [[ "$default" == "Y" || "$default" == "y" ]]; then
    suffix="[Y/n]"
  fi
  read -r -p "$prompt $suffix: " value
  value="${value:-$default}"
  case "$value" in
    y|Y|yes|YES|Yes) return 0 ;;
    *) return 1 ;;
  esac
}

install_plugin_files() {
  if [[ -d "$PROVIDER_DIR" && -d "$COMMAND_DIR" && "${AUTOROUTE_REINSTALL:-0}" != "1" ]]; then
    echo "Hermes Autoroute is already installed; skipping plugin file install."
    echo "Set AUTOROUTE_REINSTALL=1 to force-copy plugin files again."
    return
  fi

  echo "Installing Hermes plugins into $HERMES_HOME"
  mkdir -p "$HERMES_HOME/plugins/model-providers" "$HERMES_HOME/plugins"
  rm -rf "$PROVIDER_DIR" "$COMMAND_DIR"
  cp -R "$ROOT/plugins/model-providers/autoroute" "$PROVIDER_DIR"
  cp -R "$ROOT/plugins/autoroute" "$COMMAND_DIR"
  cp -R "$ROOT/src/hermes_autoroute" "$PROVIDER_DIR/hermes_autoroute"
  cp -R "$ROOT/src/hermes_autoroute" "$COMMAND_DIR/hermes_autoroute"
}

write_endpoint() {
  local mode="$1"
  local name="$2"
  local base_url="$3"
  local api_key_env="${4:-}"
  local api_key_file="${5:-}"

  ENDPOINT_MODE="$mode" \
  ENDPOINT_NAME="$name" \
  ENDPOINT_BASE_URL="$base_url" \
  ENDPOINT_API_KEY_ENV="$api_key_env" \
  ENDPOINT_API_KEY_FILE="$api_key_file" \
  CONFIG_FILE="$CONFIG_FILE" \
  "$PYTHON" <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["CONFIG_FILE"])
config = json.loads(path.read_text(encoding="utf-8"))
endpoint = {
    "name": os.environ["ENDPOINT_NAME"],
    "base_url": os.environ["ENDPOINT_BASE_URL"].rstrip("/"),
    "enabled": True,
}
if os.environ.get("ENDPOINT_API_KEY_ENV"):
    endpoint["api_key_env"] = os.environ["ENDPOINT_API_KEY_ENV"]
if os.environ.get("ENDPOINT_API_KEY_FILE"):
    endpoint["api_key_file"] = os.environ["ENDPOINT_API_KEY_FILE"]

if os.environ["ENDPOINT_MODE"] == "replace":
    config["endpoints"] = []

config.setdefault("endpoints", [])
config["endpoints"] = [item for item in config["endpoints"] if item.get("name") != endpoint["name"]]
config["endpoints"].append(endpoint)
path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

store_secret() {
  local name="$1"
  local secret_file="$SECRETS_DIR/$name.key"
  local api_key
  mkdir -p "$SECRETS_DIR"
  chmod 700 "$SECRETS_DIR"
  read -r -s -p "Paste API key for $name (input hidden): " api_key
  printf '\n'
  if [[ -z "$api_key" ]]; then
    printf '%s' ""
    return
  fi
  umask 077
  printf '%s\n' "$api_key" >"$secret_file"
  chmod 600 "$secret_file"
  printf '%s' "$secret_file"
}

setup_endpoint() {
  local mode="$1"
  local choice name base_url key_env key_file auth_choice

  cat <<EOF

Endpoint setup
  1. OpenRouter (https://openrouter.ai/api/v1)
  2. Ollama local (http://localhost:11434/v1)
  3. LM Studio local (http://localhost:1234/v1)
  4. Custom OpenAI-compatible endpoint

EOF
  choice="$(read_default "Choose endpoint type" "1")"

  case "$choice" in
    1)
      name="$(read_default "Endpoint name" "openrouter")"
      base_url="$(read_default "Base URL" "https://openrouter.ai/api/v1")"
      key_env="OPENROUTER_API_KEY"
      if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
        echo "Using existing OPENROUTER_API_KEY environment variable."
      elif yes_no "Store an OpenRouter API key in $SECRETS_DIR/$name.key?" "Y"; then
        key_file="$(store_secret "$name")"
        key_env=""
      fi
      ;;
    2)
      name="$(read_default "Endpoint name" "ollama")"
      base_url="$(read_default "Base URL" "http://localhost:11434/v1")"
      key_env=""
      ;;
    3)
      name="$(read_default "Endpoint name" "lmstudio")"
      base_url="$(read_default "Base URL" "http://localhost:1234/v1")"
      key_env=""
      ;;
    *)
      name="$(read_default "Endpoint name" "custom")"
      base_url="$(read_default "Base URL" "http://localhost:8000/v1")"
      echo "Auth method:"
      echo "  1. No auth"
      echo "  2. Environment variable"
      echo "  3. Store API key in $SECRETS_DIR"
      auth_choice="$(read_default "Choose auth method" "1")"
      case "$auth_choice" in
        2) key_env="$(read_default "API key environment variable" "OPENAI_API_KEY")" ;;
        3) key_file="$(store_secret "$name")" ;;
        *) key_env="" ;;
      esac
      ;;
  esac

  write_endpoint "$mode" "$name" "$base_url" "${key_env:-}" "${key_file:-}"
  echo "Configured endpoint '$name' at $base_url"
}

interactive_endpoint_setup() {
  if [[ ! -t 0 ]]; then
    echo "No interactive terminal detected; skipping endpoint setup."
    return
  fi

  if ! yes_no "Configure Autoroute endpoints now?" "Y"; then
    return
  fi

  local count mode action
  count="$(CONFIG_FILE="$CONFIG_FILE" "$PYTHON" <<'PY'
import json
import os
from pathlib import Path
path = Path(os.environ["CONFIG_FILE"])
print(len(json.loads(path.read_text(encoding="utf-8")).get("endpoints", [])))
PY
)"

  mode="add"
  if [[ "$count" != "0" ]]; then
    echo "Found $count existing endpoint(s)."
    action="$(read_default "Keep, add, or replace endpoints? (keep/add/replace)" "add")"
    case "$action" in
      keep|k|K) return ;;
      replace|r|R) mode="replace" ;;
      *) mode="add" ;;
    esac
  fi

  setup_endpoint "$mode"
  while yes_no "Add another endpoint?" "n"; do
    setup_endpoint "add"
  done
}

install_plugin_files

echo "Creating default Autoroute config if needed"
HERMES_HOME="$HERMES_HOME" PYTHONPATH="$ROOT/src" "$PYTHON" -m hermes_autoroute init-config >/dev/null
interactive_endpoint_setup

if command -v hermes >/dev/null 2>&1; then
  hermes plugins enable autoroute >/dev/null 2>&1 || true
fi

cat <<EOF

Hermes Autoroute installed.

Next steps:
  1. Review endpoint config if needed:
       $CONFIG_FILE
  2. Start the router with:
       hermes autoroute serve
  3. Configure Hermes:
       model.provider: autoroute
       model.model: auto

EOF
