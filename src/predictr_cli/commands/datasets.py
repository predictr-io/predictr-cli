"""Dataset endpoints — manage datasets layered on top of connections."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from predictr_cli.client import make_client
from predictr_cli.commands._helpers import ALL_PAGES_OPT, PAGE_TOKEN_OPT, emit_list
from predictr_cli.config import Config
from predictr_cli.input import read_json_input
from predictr_cli.output import emit

app = typer.Typer(no_args_is_help=True, help="Manage datasets.")

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
    """List all datasets (`GET /<org>/datasets`)."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        emit_list(
            client,
            f"/{org}/datasets",
            cfg=cfg,
            all_pages=all_pages,
            page_token=page_token,
        )


@app.command()
def get(
    ctx: typer.Context,
    dataset_id: str = typer.Argument(..., help="Dataset id"),
) -> None:
    """Get a single dataset."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/datasets/{dataset_id}")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def create(
    ctx: typer.Context,
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
) -> None:
    """Create a new dataset from a JSON document."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.post(f"/{org}/datasets", json=payload)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def update(
    ctx: typer.Context,
    dataset_id: str = typer.Argument(..., help="Dataset id"),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
) -> None:
    """Update an existing dataset."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.put(f"/{org}/datasets/{dataset_id}", json=payload)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def delete(
    ctx: typer.Context,
    dataset_id: str = typer.Argument(..., help="Dataset id"),
) -> None:
    """Delete a dataset."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.delete(f"/{org}/datasets/{dataset_id}")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def sample(
    ctx: typer.Context,
    dataset_id: str = typer.Argument(..., help="Dataset id"),
    feature: Optional[str] = typer.Option(
        None, "--feature", help="If set, sample only this feature (column)."
    ),
) -> None:
    """Fetch a small data sample for the dataset."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    params = {"feature": feature} if feature else None
    with make_client(cfg) as client:
        result = client.get(f"/{org}/datasets/{dataset_id}/sample", params=params)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def analyze(
    ctx: typer.Context,
    dataset_id: str = typer.Argument(..., help="Dataset id"),
) -> None:
    """Run automatic analysis on the dataset."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/datasets/{dataset_id}/analyze")
    emit(result, cfg.output_format, quiet=cfg.quiet)
