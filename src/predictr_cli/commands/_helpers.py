"""Shared helpers for command implementations."""

from __future__ import annotations

import sys
from typing import Any, Optional

import typer

from predictr_cli.client import Client
from predictr_cli.config import Config
from predictr_cli.output import emit

# Reusable pagination flags. Use these in a list command's signature so all
# list commands have a consistent UX around paging.
PAGE_TOKEN_OPT = typer.Option(
    None,
    "--page-token",
    help="Resume from a previous next-page-token (printed to stderr).",
)
ALL_PAGES_OPT = typer.Option(
    False,
    "--all",
    help="Fetch all pages and concatenate. Otherwise only the first page is returned.",
)

# Per-leaf `--output/-o` mirrors the top-level flag so that both
# `predictr-cli -o yaml connections list` and `predictr-cli connections list -o yaml`
# work. When set on a leaf command it overrides whatever the top-level resolved to.
OUTPUT_OPT = typer.Option(
    None,
    "--output",
    "-o",
    help="Output format for this command (json, yaml, or table). Overrides the top-level -o.",
)


def resolve_output(cfg: Config, override: Optional[str]) -> str:
    """Return the output format to use: the per-leaf override when given, else cfg's."""
    return override if override else cfg.output_format


def emit_list(
    client: Client,
    path: str,
    *,
    cfg: Config,
    all_pages: bool = False,
    page_token: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
    output_override: Optional[str] = None,
) -> None:
    """Fetch a list endpoint and emit, transparently handling pagination.

    `--all` follows the next-page chain and concatenates everything.
    Otherwise we fetch one page; if the server gave us a next-page token,
    print it on stderr so the user can pass it back via --page-token.
    """
    fmt = resolve_output(cfg, output_override)
    if all_pages:
        items = list(client.paginate(path, params=params))
        emit(items, fmt, quiet=cfg.quiet)
        return

    body, next_token = client.get_page(path, page_token=page_token, params=params)
    if next_token and not cfg.quiet:
        # Hint goes to stderr so it doesn't pollute piped JSON output.
        print(
            f"# more results available; resume with --page-token {next_token}",
            file=sys.stderr,
        )
    emit(body, fmt, quiet=cfg.quiet)
