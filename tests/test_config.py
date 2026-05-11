"""Tests for config resolution precedence and error cases."""

from __future__ import annotations

import pytest

from predictr_cli.config import (
    DEFAULT_API_URL,
    DEFAULT_MAX_RETRIES,
    Config,
    ConfigError,
    resolve_config,
)


def test_defaults_apply_when_nothing_set(monkeypatch):
    monkeypatch.delenv("PREDICTR_API_KEY", raising=False)
    monkeypatch.delenv("PREDICTR_API_URL", raising=False)
    monkeypatch.delenv("PREDICTR_ORG", raising=False)
    monkeypatch.delenv("PREDICTR_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("PREDICTR_MAX_RETRIES", raising=False)
    monkeypatch.delenv("PREDICTR_OUTPUT", raising=False)
    # Bypass any user config file the test machine happens to have.
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})

    cfg = resolve_config()

    assert cfg.api_url == DEFAULT_API_URL
    assert cfg.api_key is None
    assert cfg.org_name is None
    assert cfg.max_retries == DEFAULT_MAX_RETRIES
    assert cfg.output_format == "json"


def test_env_var_used_when_flag_missing(monkeypatch):
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    monkeypatch.setenv("PREDICTR_API_KEY", "from-env")
    monkeypatch.setenv("PREDICTR_ORG", "acme")

    cfg = resolve_config()

    assert cfg.api_key == "from-env"
    assert cfg.org_name == "acme"


def test_flag_beats_env_var(monkeypatch):
    monkeypatch.setattr("predictr_cli.config._load_file_config", lambda: {})
    monkeypatch.setenv("PREDICTR_API_KEY", "from-env")
    monkeypatch.setenv("PREDICTR_ORG", "from-env-org")

    cfg = resolve_config(api_key="from-flag", org_name="from-flag-org")

    assert cfg.api_key == "from-flag"
    assert cfg.org_name == "from-flag-org"


def test_env_beats_config_file(monkeypatch):
    monkeypatch.setattr(
        "predictr_cli.config._load_file_config",
        lambda: {"api_key": "from-file", "org_name": "from-file-org"},
    )
    monkeypatch.setenv("PREDICTR_API_KEY", "from-env")
    # leave PREDICTR_ORG unset so file should win for org

    monkeypatch.delenv("PREDICTR_ORG", raising=False)
    cfg = resolve_config()

    assert cfg.api_key == "from-env"
    assert cfg.org_name == "from-file-org"


def test_require_org_raises_when_missing():
    cfg = Config(
        api_url=DEFAULT_API_URL,
        org_name=None,
        api_key="x",
        bearer_token=None,
        output_format="json",
        verbose=False,
        quiet=False,
        max_retries=3,
        no_retry=False,
    )
    with pytest.raises(ConfigError, match="No organisation"):
        cfg.require_org()


def test_require_auth_prefers_bearer_token():
    cfg = Config(
        api_url=DEFAULT_API_URL,
        org_name="acme",
        api_key="api-key-value",
        bearer_token="bearer-value",
        output_format="json",
        verbose=False,
        quiet=False,
        max_retries=3,
        no_retry=False,
    )
    name, value = cfg.require_auth()
    assert name == "Authorization"
    assert value == "Bearer bearer-value"


def test_require_auth_falls_back_to_api_key():
    cfg = Config(
        api_url=DEFAULT_API_URL,
        org_name="acme",
        api_key="api-key-value",
        bearer_token=None,
        output_format="json",
        verbose=False,
        quiet=False,
        max_retries=3,
        no_retry=False,
    )
    name, value = cfg.require_auth()
    assert name == "x-api-key"
    assert value == "api-key-value"


def test_require_auth_raises_with_no_credentials():
    cfg = Config(
        api_url=DEFAULT_API_URL,
        org_name="acme",
        api_key=None,
        bearer_token=None,
        output_format="json",
        verbose=False,
        quiet=False,
        max_retries=3,
        no_retry=False,
    )
    with pytest.raises(ConfigError, match="No credentials"):
        cfg.require_auth()
