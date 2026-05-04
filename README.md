# predictr-cli

Command-line interface for the [predictr.io](https://predictr.io) API.

`predictr-cli` is a thin wrapper over the REST API with a few quality-of-life
additions: layered configuration, automatic retry/backoff for transient
failures, and clean exit codes for scripting.

## Installation

```bash
pip install predictr-cli            # once published
pip install -e ".[dev]"        # local development
```

## Configuration

Configuration is resolved in priority order:

1. CLI flag (e.g. `--api-key`, `--org-name`)
2. Environment variable (e.g. `PREDICTR_API_KEY`)
3. Config file at `~/.config/predictr-cli/config.toml`
4. Built-in defaults

### Authentication

Either a long-lived API key (preferred) or a session bearer token:

```bash
export PREDICTR_API_KEY="psk_..."
# or
export PREDICTR_BEARER_TOKEN="eyJ..."
```

You can copy a bearer token from the **Copy API Token** menu item in the
predictr.io web UI.

### Default organisation

Most commands operate against an organisation. Set it once and forget it:

```bash
export PREDICTR_ORG="my-org"
```

Override per-invocation with `--org-name <name>`.

### Config file (optional)

```toml
# ~/.config/predictr-cli/config.toml
api_url     = "https://api.predictr.io"
api_key     = "psk_..."
org_name    = "my-org"
output_format = "json"
max_retries = 3
```

## Usage

```bash
predictr-cli --help

# Server info — useful smoke test (doesn't need an org)
predictr-cli meta info

# Capabilities for the current org (plan, limits, trial days remaining)
predictr-cli capabilities

# Connections
predictr-cli connections list
predictr-cli connections get <conn-id>
predictr-cli connections create --input-file new-conn.json
predictr-cli connections update <conn-id> --data '{"conn_name": "renamed"}'
predictr-cli connections delete <conn-id>
predictr-cli connections test <conn-id>
predictr-cli connections crawl <conn-id>
predictr-cli connections tables <conn-id>
predictr-cli connections columns <conn-id> --table orders

# Datasets
predictr-cli datasets list
predictr-cli datasets get <dataset-id>
predictr-cli datasets create --input-file dataset.json
predictr-cli datasets sample <dataset-id>
predictr-cli datasets analyze <dataset-id>
predictr-cli datasets delete <dataset-id>

# File uploads (for fileupload connections)
predictr-cli connections upload <conn-id> --file data.csv

# Models
predictr-cli models list
predictr-cli models get <model-id>
predictr-cli models create --input-file model.json
predictr-cli models predict <model-id> --input-file features.json
predictr-cli models update <model-id> --input-file model.json   # PUT (replace)
predictr-cli models update <model-id> --patch --data '{...}'     # PATCH (merge)
predictr-cli models delete <model-id>

# Workflows
predictr-cli workflows list
predictr-cli workflows get <wf-id>
predictr-cli workflows create --input-file workflow.json
predictr-cli workflows run <wf-id>
predictr-cli workflows history <wf-id>
predictr-cli workflows history <wf-id> <run-id>
predictr-cli workflows schedule <wf-id> --input-file schedule.json
predictr-cli workflows unschedule <wf-id>
predictr-cli workflows zoneinfo

# Analysis slates
predictr-cli mba list                                     # market basket
predictr-cli mba create --input-file mba.json
predictr-cli mba fit <id>
predictr-cli mba rules <id>
predictr-cli mba items <id>

predictr-cli rfm list                                     # RFM clustering
predictr-cli rfm create --input-file rfm.json
predictr-cli rfm fit <id>
predictr-cli rfm guess-schema <conn-id>
predictr-cli rfm delete <id> --model-id <model-id>        # delete one fit only

predictr-cli salesforecast list
predictr-cli salesforecast create --input-file sf.json
predictr-cli salesforecast fit <id>
predictr-cli salesforecast holidays                       # supported countries
predictr-cli salesforecast holidays GB                    # holidays for GB
```

### Complex JSON input

Three equivalent ways to pass a JSON payload:

```bash
# From a file
predictr-cli connections create --input-file new-conn.json

# Inline
predictr-cli connections create --data '{"conn_name":"prod","conn_type":"snowflake"}'

# From stdin (pipe-friendly)
cat new-conn.json | predictr-cli connections create --input-file -
```

### Output formats

```bash
predictr-cli connections list                    # JSON (default)
predictr-cli connections list --output yaml      # YAML
predictr-cli connections list --output table     # Aligned table
```

JSON output is pretty-printed when stdout is a TTY; raw and pipe-friendly
otherwise. So this just works:

```bash
predictr-cli connections list | jq '.[].conn_id'
```

### Retry behaviour

Transient failures (network errors, 5xx, 429) are retried with
exponential backoff. 4xx responses fail immediately.

```bash
predictr-cli --max-retries 5 datasets list       # Override retry count
predictr-cli --no-retry datasets list            # Disable retries entirely
PREDICTR_MAX_RETRIES=0 predictr-cli ...          # Equivalent to --no-retry
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User/configuration error (missing org, bad input) |
| 2 | API error (4xx response) |
| 3 | Network error / retries exhausted |

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
```
