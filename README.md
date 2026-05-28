# Hermes Autoroute

Hermes Autoroute is a Hermes-native plugin pair:

- `plugins/model-providers/autoroute` registers a real Hermes model provider named `autoroute`.
- `plugins/autoroute` registers `hermes autoroute ...` management commands and `/autoroute` diagnostics.

The provider points Hermes at a local OpenAI-compatible router. The router scans configured endpoints, enriches model metadata from public catalogs, probes health/capabilities, scores each request, then forwards the call to the best healthy downstream model with fallbacks.

## One-command install

From a local checkout:

```bash
./scripts/install.sh
```

The installer:

- detects an existing Hermes Autoroute install and skips file copying unless
  `AUTOROUTE_REINSTALL=1` is set
- copies the Hermes provider plugin into `$HERMES_HOME/plugins/model-providers/autoroute`
- copies the command plugin into `$HERMES_HOME/plugins/autoroute`
- vendors the Autoroute Python package inside those plugin directories
- creates `$HERMES_HOME/autoroute/config.json` if it does not exist
- interactively configures one or more OpenAI-compatible endpoints
- can store endpoint API keys in `$HERMES_HOME/autoroute/secrets/*.key`
  with `0600` permissions

The installer does not write into system Python, so it works on PEP 668
externally-managed Python installs.

Then configure Hermes:

```yaml
model:
  provider: autoroute
  model: auto
```

Start the local router:

```bash
hermes autoroute serve
```

## Install manually

```bash
mkdir -p "$HERMES_HOME/plugins/model-providers" "$HERMES_HOME/plugins"
cp -R plugins/model-providers/autoroute "$HERMES_HOME/plugins/model-providers/"
cp -R plugins/autoroute "$HERMES_HOME/plugins/"
cp -R src/hermes_autoroute "$HERMES_HOME/plugins/model-providers/autoroute/hermes_autoroute"
cp -R src/hermes_autoroute "$HERMES_HOME/plugins/autoroute/hermes_autoroute"
PYTHONPATH=src python3 -m hermes_autoroute init-config
hermes plugins enable autoroute
```

Set Hermes to use the provider:

```yaml
model:
  provider: autoroute
  model: auto
```

Start the local router:

```bash
hermes autoroute serve
```

Or outside Hermes:

```bash
PYTHONPATH=src python3 -m hermes_autoroute serve
```

## Install from GitHub

After cloning the repository:

```bash
git clone https://github.com/nathanteeples/hermes-autoroute.git
cd hermes-autoroute
./scripts/install.sh
```

## Config

By default, Autoroute reads `$HERMES_HOME/autoroute/config.json`, or the path in `HERMES_AUTOROUTE_CONFIG`.

The installer can write this for you. Minimal config:

```json
{
  "endpoints": [
    {
      "name": "openrouter",
      "base_url": "https://openrouter.ai/api/v1",
      "api_key_file": "/home/you/.hermes/autoroute/secrets/openrouter.key",
      "enabled": true
    },
    {
      "name": "local",
      "base_url": "http://localhost:11434/v1",
      "enabled": true
    }
  ]
}
```

For API keys, each endpoint may use either:

- `api_key_env`: read a bearer token from an environment variable
- `api_key_file`: read a bearer token from a local secret file

Useful commands:

```bash
hermes autoroute init-config
hermes autoroute scan
hermes autoroute probe
hermes autoroute status
hermes autoroute models
hermes autoroute explain --last
```
