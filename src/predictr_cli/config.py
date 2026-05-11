"""Configuration resolution.

Precedence (highest first):
  1. CLI flags
  2. Environment variables (PREDICTR_*)
  3. Config file (~/.config/predictr-cli/config.toml)
  4. Built-in defaults
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

DEFAULT_API_URL = "https://api.predictr.io"
DEFAULT_MAX_RETRIES = 3
DEFAULT_OUTPUT = "json"

CONFIG_PATH = Path.home() / ".config" / "predictr-cli" / "config.toml"


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass
class Config:
    """Resolved runtime configuration for a single CLI invocation."""

    api_url: str
    org_name: Optional[str]
    api_key: Optional[str]
    bearer_token: Optional[str]
    output_format: str
    verbose: bool
    quiet: bool
    max_retries: int
    no_retry: bool

    def require_org(self) -> str:
        """Return org_name or raise a clear error if not set."""
        if not self.org_name:
            raise ConfigError(
                "No organisation specified. "
                "Set PREDICTR_ORG or pass --org-name."
            )
        return self.org_name

    def require_auth(self) -> tuple[str, str]:
        """Return (header_name, header_value) for auth, or raise."""
        if self.bearer_token:
            return ("Authorization", f"Bearer {self.bearer_token}")
        if self.api_key:
            return ("x-api-key", self.api_key)
        raise ConfigError(
            "No credentials specified. "
            "Set PREDICTR_API_KEY (or PREDICTR_BEARER_TOKEN) or pass --api-key/--bearer-token."
        )


def _load_file_config() -> dict[str, Any]:
    """Load the optional TOML config file. Returns {} if missing or unreadable."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with CONFIG_PATH.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        # Don't crash for a malformed config file; warn and ignore.
        print(f"warning: could not read {CONFIG_PATH}: {exc}", file=sys.stderr)
        return {}


def _pick(*values: Any) -> Any:
    """Return the first non-None, non-empty value."""
    for v in values:
        if v not in (None, ""):
            return v
    return None


def resolve_config(
    *,
    api_url: Optional[str] = None,
    org_name: Optional[str] = None,
    api_key: Optional[str] = None,
    bearer_token: Optional[str] = None,
    output_format: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    max_retries: Optional[int] = None,
    no_retry: bool = False,
) -> Config:
    """Resolve final config from CLI flags, env vars, config file, defaults.

    All keyword args here come from CLI flags; the function fills in the rest.
    """
    file_cfg = _load_file_config()
    env = os.environ

    return Config(
        api_url=_pick(
            api_url,
            env.get("PREDICTR_API_URL"),
            file_cfg.get("api_url"),
            DEFAULT_API_URL,
        ),
        org_name=_pick(
            org_name,
            env.get("PREDICTR_ORG"),
            file_cfg.get("org_name"),
        ),
        api_key=_pick(
            api_key,
            env.get("PREDICTR_API_KEY"),
            file_cfg.get("api_key"),
        ),
        bearer_token=_pick(
            bearer_token,
            env.get("PREDICTR_BEARER_TOKEN"),
            file_cfg.get("bearer_token"),
        ),
        output_format=_pick(
            output_format,
            env.get("PREDICTR_OUTPUT"),
            file_cfg.get("output_format"),
            DEFAULT_OUTPUT,
        ),
        verbose=verbose,
        quiet=quiet,
        max_retries=int(
            _pick(
                max_retries,
                env.get("PREDICTR_MAX_RETRIES"),
                file_cfg.get("max_retries"),
                DEFAULT_MAX_RETRIES,
            )
        ),
        no_retry=no_retry,
    )
