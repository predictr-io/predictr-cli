"""Shared helpers for command implementations."""

from __future__ import annotations

import sys
from typing import Any, Optional

import typer

from pebbles.client import Client
from pebbles.config import Config
from pebbles.output import emit

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


def emit_list(
    client: Client,
    path: str,
    *,
    cfg: Config,
    all_pages: bool = False,
    page_token: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
) -> None:
    """Fetch a list endpoint and emit, transparently handling pagination.

    `--all` follows the next-page chain and concatenates everything.
    Otherwise we fetch one page; if the server gave us a next-page token,
    print it on stderr so the user can pass it back via --page-token.
    """
    if all_pages:
        items = list(client.paginate(path, params=params))
        emit(items, cfg.output_format, quiet=cfg.quiet)
        return

    body, next_token = client.get_page(path, page_token=page_token, params=params)
    if next_token and not cfg.quiet:
        # Hint goes to stderr so it doesn't pollute piped JSON output.
        print(
            f"# more results available; resume with --page-token {next_token}",
            file=sys.stderr,
        )
    emit(body, cfg.output_format, quiet=cfg.quiet)
