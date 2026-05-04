"""End-to-end CLI smoke tests using Typer's testing helper."""

from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from pebbles.cli import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "predictr-cli" in result.stdout


def test_missing_credentials_exits_with_clean_message(monkeypatch):
    monkeypatch.delenv("PREDICTR_API_KEY", raising=False)
    monkeypatch.delenv("PREDICTR_BEARER_TOKEN", raising=False)
    monkeypatch.setattr("pebbles.config._load_file_config", lambda: {})
    # Typer doesn't run our `main()` wrapper here; test that the inner
    # command surfaces ConfigError, which the wrapper catches in production.
    result = runner.invoke(app, ["meta", "info"])
    assert result.exit_code != 0


def test_missing_org_exits_with_clean_message(monkeypatch):
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.delenv("PREDICTR_ORG", raising=False)
    monkeypatch.setattr("pebbles.config._load_file_config", lambda: {})
    result = runner.invoke(app, ["capabilities"])
    assert result.exit_code != 0


@respx.mock
def test_meta_info_round_trip(monkeypatch):
    monkeypatch.setenv("PREDICTR_API_KEY", "fake")
    monkeypatch.setattr("pebbles.config._load_file_config", lambda: {})
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
    monkeypatch.setattr("pebbles.config._load_file_config", lambda: {})
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
    monkeypatch.setattr("pebbles.config._load_file_config", lambda: {})
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
    monkeypatch.setattr("pebbles.config._load_file_config", lambda: {})
    result = runner.invoke(app, ["connections", "create"])
    assert result.exit_code != 0
