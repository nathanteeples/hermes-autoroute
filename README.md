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

- installs the Python package in editable mode
- copies the Hermes provider plugin into `$HERMES_HOME/plugins/model-providers/autoroute`
- copies the command plugin into `$HERMES_HOME/plugins/autoroute`
- creates `$HERMES_HOME/autoroute/config.json` if it does not exist

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
pip install -e .
mkdir -p "$HERMES_HOME/plugins/model-providers" "$HERMES_HOME/plugins"
cp -R plugins/model-providers/autoroute "$HERMES_HOME/plugins/model-providers/"
cp -R plugins/autoroute "$HERMES_HOME/plugins/"
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
hermes-autoroute serve
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

Minimal config:

```json
{
  "endpoints": [
    {
      "name": "openrouter",
      "base_url": "https://openrouter.ai/api/v1",
      "api_key_env": "OPENROUTER_API_KEY",
      "enabled": true
    },
    {
      "name": "local",
      "base_url": "http://localhost:11434/v1",
      "api_key_env": "OLLAMA_API_KEY",
      "enabled": true
    }
  ]
}
```

Useful commands:

```bash
hermes autoroute init-config
hermes autoroute scan
hermes autoroute probe
hermes autoroute status
hermes autoroute models
hermes autoroute explain --last
```
