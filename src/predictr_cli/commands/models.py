"""Model endpoints — manage data-mining models and run predictions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from predictr_cli.client import make_client
from predictr_cli.commands._helpers import ALL_PAGES_OPT, PAGE_TOKEN_OPT, emit_list
from predictr_cli.config import Config
from predictr_cli.input import read_json_input
from predictr_cli.output import emit

app = typer.Typer(no_args_is_help=True, help="Manage data-mining models.")

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
    """List all models."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        emit_list(
            client,
            f"/{org}/models",
            cfg=cfg,
            all_pages=all_pages,
            page_token=page_token,
        )


@app.command()
def get(
    ctx: typer.Context,
    model_id: str = typer.Argument(..., help="Model id"),
) -> None:
    """Get a single model."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/models/{model_id}")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def create(
    ctx: typer.Context,
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
    fit_now: bool = typer.Option(
        True,
        "--fit-now/--no-fit-now",
        help="Whether to fit the model immediately. Default: fit-now.",
    ),
    model_build_infra: Optional[str] = typer.Option(
        None,
        "--model-build-infra",
        help="Container size (s/m/l/xl/xxl) or JSON backend spec for the fit job.",
    ),
) -> None:
    """Create a new model from a JSON document."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    params: dict[str, str] = {"fit_now": "true" if fit_now else "false"}
    if model_build_infra:
        params["model_build_infra"] = model_build_infra
    with make_client(cfg) as client:
        result = client.post(f"/{org}/models", json=payload, params=params)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def update(
    ctx: typer.Context,
    model_id: str = typer.Argument(..., help="Model id"),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
    patch: bool = typer.Option(
        False, "--patch", help="Use PATCH (partial update) instead of PUT (replace)."
    ),
) -> None:
    """Update an existing model. Defaults to PUT (replace); pass --patch for PATCH."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        if patch:
            result = client.patch(f"/{org}/models/{model_id}", json=payload)
        else:
            result = client.put(f"/{org}/models/{model_id}", json=payload)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def delete(
    ctx: typer.Context,
    model_id: str = typer.Argument(..., help="Model id"),
) -> None:
    """Delete a model."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.delete(f"/{org}/models/{model_id}")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def predict(
    ctx: typer.Context,
    model_id: str = typer.Argument(..., help="Model id"),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
) -> None:
    """Run a prediction with the given input payload."""
    cfg: Config = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.post(f"/{org}/models/{model_id}/predict", json=payload)
    emit(result, cfg.output_format, quiet=cfg.quiet)
