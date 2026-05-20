"""End-to-end CLI smoke tests using Typer's testing helper."""

from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from predictr_cli.cli import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "predictr-cli" in result.stdout


def test_missing_credentials_exits_with_clean_message(monkeypatch):
    monkeypatch.delenv("PREDICTR_API_KEY", raising=False)
    monkeypatch.delenv("PREDICTR_BEARER_TOKEN", raising=False)
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    # Typer doesn't run our `main()` wrapper here; test that the inner
    # command surfaces ConfigError, which the wrapper catches in production.
    result = runner.invoke(app, ["meta", "info"])
    assert result.exit_code != 0


def test_missing_org_exits_with_clean_message(monkeypatch):
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.delenv("PREDICTR_ORG", raising=False)
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    result = runner.invoke(app, ["capabilities"])
    assert result.exit_code != 0


@respx.mock
def test_meta_info_round_trip(monkeypatch):
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    respx.get("https://api.predictr.io/meta").mock(
        return_value=httpx.Response(200, json={"version": "1.0"})
    )
    result = runner.invoke(app, ["meta", "info"])
    assert result.exit_code == 0
    assert "version" in result.stdout


@respx.mock
def test_connections_list_round_trip(monkeypatch):
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.setenv("PREDICTR_ORG", "acme")
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    respx.get("https://api.predictr.io/acme/connections").mock(
        return_value=httpx.Response(200, json=[{"id": "c1", "name": "snowflake-prod"}])
    )
    result = runner.invoke(app, ["connections", "list"])
    assert result.exit_code == 0
    assert "snowflake-prod" in result.stdout


@respx.mock
def test_connections_create_with_inline_data(monkeypatch):
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.setenv("PREDICTR_ORG", "acme")
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    route = respx.post("https://api.predictr.io/acme/connections").mock(
        return_value=httpx.Response(200, json={"id": "new", "name": "test"})
    )
    result = runner.invoke(
        app,
        ["connections", "create", "--data", '{"name": "test", "type": "snowflake"}'],
    )
    assert result.exit_code == 0
    import json
    sent = json.loads(route.calls.last.request.content.decode())
    assert sent == {"name": "test", "type": "snowflake"}


def test_connections_create_with_no_input_errors(monkeypatch):
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.setenv("PREDICTR_ORG", "acme")
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    result = runner.invoke(app, ["connections", "create"])
    assert result.exit_code != 0


# --------------------------------------------------------------------------- #
# Per-leaf `--output/-o` works on the right of the subcommand (regression).
# --------------------------------------------------------------------------- #
@respx.mock
def test_connections_list_accepts_output_flag_on_the_leaf(monkeypatch):
    """Regression: `connections list --output yaml` must work, not only the
    pre-subcommand `-o yaml connections list`."""
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.setenv("PREDICTR_ORG", "acme")
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    respx.get("https://api.predictr.io/acme/connections").mock(
        return_value=httpx.Response(200, json=[{"id": "c1", "name": "snowflake-prod"}])
    )
    result = runner.invoke(app, ["connections", "list", "--output", "yaml"])
    assert result.exit_code == 0
    # YAML output uses block-style "key: value" rather than JSON's {"key": "value"}.
    assert "name: snowflake-prod" in result.stdout
    # And short form too:
    result = runner.invoke(app, ["connections", "list", "-o", "yaml"])
    assert result.exit_code == 0
    assert "name: snowflake-prod" in result.stdout


# --------------------------------------------------------------------------- #
# Schema parameter is sent as `schema_name` (the canonical name; mr-slate also
# accepts plain `schema` for backward compat) and `columns` finally has a
# --schema flag.
# --------------------------------------------------------------------------- #
@respx.mock
def test_columns_sends_table_and_schema_name(monkeypatch):
    """Regression: `connections columns -t T -s main` sends both table AND
    schema_name (the schema flag was missing entirely before this fix)."""
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.setenv("PREDICTR_ORG", "acme")
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    route = respx.get("https://api.predictr.io/acme/connections/c1/columns").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = runner.invoke(
        app, ["connections", "columns", "c1", "-t", "test_table", "-s", "main"]
    )
    assert result.exit_code == 0, result.output
    # Inspect the actual outbound query string so we catch wrong param names.
    req = route.calls.last.request
    assert req.url.params["table"] == "test_table"
    assert req.url.params["schema_name"] == "main"


@respx.mock
def test_table_sample_sends_schema_name_not_schema(monkeypatch):
    """Regression: `connections table-sample` previously sent `schema=` to an
    endpoint that wanted `schema_name=`, returning 422. Verify canonical name."""
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.setenv("PREDICTR_ORG", "acme")
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    route = respx.get(
        "https://api.predictr.io/acme/connections/c1/tables/test_table/sample"
    ).mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(
        app, ["connections", "table-sample", "c1", "test_table", "-s", "main"]
    )
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.url.params["schema_name"] == "main"
    assert "schema" not in [
        k for k in route.calls.last.request.url.params.keys() if k != "schema_name"
    ]


@respx.mock
def test_table_sends_schema_name(monkeypatch):
    """The combined /tables/<t> endpoint also gets `schema_name=` for consistency."""
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.setenv("PREDICTR_ORG", "acme")
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    route = respx.get(
        "https://api.predictr.io/acme/connections/c1/tables/test_table"
    ).mock(return_value=httpx.Response(200, json={"columns": [], "rows": []}))
    result = runner.invoke(
        app, ["connections", "table", "c1", "test_table", "-s", "main"]
    )
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.url.params["schema_name"] == "main"
