#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PYTHON="${PYTHON:-python3}"

echo "Installing Hermes Autoroute package from $ROOT"
"$PYTHON" -m pip install -e "$ROOT"

echo "Installing Hermes plugins into $HERMES_HOME"
mkdir -p "$HERMES_HOME/plugins/model-providers" "$HERMES_HOME/plugins"
rm -rf "$HERMES_HOME/plugins/model-providers/autoroute" "$HERMES_HOME/plugins/autoroute"
cp -R "$ROOT/plugins/model-providers/autoroute" "$HERMES_HOME/plugins/model-providers/autoroute"
cp -R "$ROOT/plugins/autoroute" "$HERMES_HOME/plugins/autoroute"

echo "Creating default Autoroute config if needed"
HERMES_HOME="$HERMES_HOME" "$PYTHON" -m hermes_autoroute init-config >/dev/null

cat <<EOF

Hermes Autoroute installed.

Next steps:
  1. Edit $HERMES_HOME/autoroute/config.json and add your endpoints.
  2. Start the router with:
       hermes autoroute serve
  3. Configure Hermes:
       model.provider: autoroute
       model.model: auto

EOF

