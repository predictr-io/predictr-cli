"""Top-level Typer app and global options.

All commands receive the resolved Config via Typer's context object
(`ctx.obj`) — see the `_GlobalOptions` callback below.
"""

from __future__ import annotations

import sys
from typing import Optional

import typer

from pebbles import __version__
from pebbles.client import APIError
from pebbles.commands import (
    connections,
    datasets,
    mba,
    meta,
    models,
    rfm,
    salesforecast,
    workflows,
)
from pebbles.config import ConfigError, resolve_config
from pebbles.output import emit_error

app = typer.Typer(
    name="predictr-cli",
    help="Command-line interface for the predictr.io API.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"predictr-cli {__version__}")
        raise typer.Exit()


@app.callback()
def _global_options(
    ctx: typer.Context,
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        envvar="PREDICTR_API_KEY",
        help="API key (sent as x-api-key). Falls back to PREDICTR_API_KEY.",
        show_envvar=False,
    ),
    bearer_token: Optional[str] = typer.Option(
        None,
        "--bearer-token",
        envvar="PREDICTR_BEARER_TOKEN",
        help="Bearer token (sent as Authorization: Bearer ...).",
        show_envvar=False,
    ),
    org_name: Optional[str] = typer.Option(
        None,
        "--org-name",
        envvar="PREDICTR_ORG",
        help="Organisation name. Falls back to PREDICTR_ORG.",
        show_envvar=False,
    ),
    api_url: Optional[str] = typer.Option(
        None,
        "--api-url",
        envvar="PREDICTR_API_URL",
        help="API base URL. Falls back to PREDICTR_API_URL.",
        show_envvar=False,
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json (default), yaml, or table.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show request URLs on stderr."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error output."),
    max_retries: Optional[int] = typer.Option(
        None,
        "--max-retries",
        envvar="PREDICTR_MAX_RETRIES",
        help="Max retries for retryable failures (default 3).",
        show_envvar=False,
    ),
    no_retry: bool = typer.Option(False, "--no-retry", help="Disable retries entirely."),
    _version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Resolve and stash global config on the Typer context for all commands."""
    ctx.obj = resolve_config(
        api_url=api_url,
        org_name=org_name,
        api_key=api_key,
        bearer_token=bearer_token,
        output_format=output,
        verbose=verbose,
        quiet=quiet,
        max_retries=max_retries,
        no_retry=no_retry,
    )


# --------------------------------------------------------------------------- #
# Sub-command groups (one per resource family)
# --------------------------------------------------------------------------- #
app.add_typer(meta.app, name="meta", help="Server meta info & schemas.")
app.add_typer(connections.app, name="connections", help="Manage data source connections.")
app.add_typer(datasets.app, name="datasets", help="Manage datasets.")
app.add_typer(models.app, name="models", help="Manage models and run predictions.")
app.add_typer(workflows.app, name="workflows", help="Manage workflows (orchestration).")
app.add_typer(mba.app, name="mba", help="Market Basket Analysis.")
app.add_typer(rfm.app, name="rfm", help="RFM clustering analysis.")
app.add_typer(salesforecast.app, name="salesforecast", help="Sales forecasting analysis.")


# --------------------------------------------------------------------------- #
# Top-level convenience commands
# --------------------------------------------------------------------------- #
@app.command()
def capabilities(ctx: typer.Context) -> None:
    """Show capabilities (plan, limits, trial days remaining) for the current org."""
    from pebbles.client import make_client
    from pebbles.output import emit

    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/capabilities")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def analyses(ctx: typer.Context) -> None:
    """List ALL analyses across all slates (mba/rfm/salesforecast) for the current org."""
    from pebbles.client import make_client
    from pebbles.output import emit

    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/analysis")
    emit(result, cfg.output_format, quiet=cfg.quiet)


# --------------------------------------------------------------------------- #
# Top-level error handler — translate our exceptions to clean exits
# --------------------------------------------------------------------------- #
def main() -> None:
    """Wrap the Typer app to map our exception types onto exit codes.

    Exit codes:
      0 — success
      1 — user/configuration error (missing org, bad input)
      2 — API error (4xx/5xx response we won't retry)
      3 — network error / retries exhausted
    """
    try:
        app()
    except ConfigError as exc:
        emit_error(str(exc))
        sys.exit(1)
    except APIError as exc:
        emit_error(str(exc))
        sys.exit(3 if exc.status_code == 0 else 2)


if __name__ == "__main__":
    main()
