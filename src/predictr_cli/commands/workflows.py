"""Workflow endpoints — orchestration: schedule, run, history."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from predictr_cli.client import make_client
from predictr_cli.commands._helpers import ALL_PAGES_OPT, PAGE_TOKEN_OPT, emit_list
from predictr_cli.config import Config
from predictr_cli.input import read_json_input
from predictr_cli.output import emit

app = typer.Typer(no_args_is_help=True, help="Manage workflows (orchestrated jobs).")

_INPUT_FILE_OPT = typer.Option(
    None, "--input-file", "-f", help="Path to a JSON file (or '-' for stdin)."
)
_DATA_OPT = typer.Option(
    None, "--data", "-d", help="Inline JSON (alternative to --input-file)."
)


@app.command("list")
def list_(
    ctx: typer.Context,
    page_token: Optional[str] = PAGE_TOKEN_OPT,
    all_pages: bool = ALL_PAGES_OPT,
) -> None:
    """List all workflows."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        emit_list(
            client,
            f"/{org}/workflow",
            cfg=cfg,
            all_pages=all_pages,
            page_token=page_token,
        )


@app.command()
def get(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow id"),
) -> None:
    """Get a single workflow."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/workflow/{workflow_id}")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def create(
    ctx: typer.Context,
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
) -> None:
    """Create a new workflow from a JSON document."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.post(f"/{org}/workflow", json=payload)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def update(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow id"),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
) -> None:
    """Update a workflow (PATCH semantics)."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.patch(f"/{org}/workflow/{workflow_id}", json=payload)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def delete(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow id"),
) -> None:
    """Delete a workflow."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.delete(f"/{org}/workflow/{workflow_id}")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def run(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow id"),
) -> None:
    """Trigger a one-off run of the workflow."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.post(f"/{org}/workflow/{workflow_id}/run")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def history(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow id"),
    run_id: Optional[str] = typer.Argument(None, help="Specific run id (optional)"),
) -> None:
    """Show run history for a workflow, or details of a single run."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    path = f"/{org}/workflow/{workflow_id}/history"
    if run_id:
        path = f"{path}/{run_id}"
    with make_client(cfg) as client:
        result = client.get(path)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def schedule(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow id"),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
) -> None:
    """Schedule a workflow (cron-style; pass schedule JSON via --input-file or --data)."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.post(f"/{org}/workflow/{workflow_id}/schedule", json=payload)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def unschedule(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow id"),
) -> None:
    """Remove the schedule from a workflow."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.post(f"/{org}/workflow/{workflow_id}/unschedule")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def zoneinfo(ctx: typer.Context) -> None:
    """List supported timezone strings (useful when defining schedules)."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/workflow/zoneinfo")
    emit(result, cfg.output_format, quiet=cfg.quiet)
