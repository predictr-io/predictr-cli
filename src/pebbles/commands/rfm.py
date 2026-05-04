"""RFM (Recency, Frequency, Monetary) clustering analysis endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import typer

from pebbles.client import make_client
from pebbles.commands._helpers import ALL_PAGES_OPT, PAGE_TOKEN_OPT, emit_list
from pebbles.input import read_json_input
from pebbles.output import emit

app = typer.Typer(no_args_is_help=True, help="RFM clustering analysis.")

_PREFIX = "/analysis/rfmcluster"

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
    """List all RFM analyses."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        emit_list(
            client,
            f"/{org}{_PREFIX}",
            cfg=cfg,
            all_pages=all_pages,
            page_token=page_token,
        )


@app.command()
def get(
    ctx: typer.Context,
    analysis_id: str = typer.Argument(..., help="RFM analysis id"),
    ml_model_id: Optional[str] = typer.Option(
        None, "--ml-model-id", help="Specific fit run (defaults to the active model)."
    ),
) -> None:
    """Get a single RFM analysis."""
    cfg = ctx.obj
    org = cfg.require_org()
    params = {"ml_model_id": ml_model_id} if ml_model_id else None
    with make_client(cfg) as client:
        result = client.get(f"/{org}{_PREFIX}/{analysis_id}", params=params)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def create(
    ctx: typer.Context,
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
    model_build_infra: Optional[str] = typer.Option(
        None,
        "--model-build-infra",
        help="Container size (s/m/l/xl/xxl) or JSON backend spec for the fit job.",
    ),
) -> None:
    """Create a new RFM analysis."""
    cfg = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    params = {"model_build_infra": model_build_infra} if model_build_infra else None
    with make_client(cfg) as client:
        result = client.post(f"/{org}{_PREFIX}", json=payload, params=params)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def update(
    ctx: typer.Context,
    analysis_id: str = typer.Argument(..., help="RFM analysis id"),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
) -> None:
    """Update an RFM analysis (PATCH)."""
    cfg = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.patch(f"/{org}{_PREFIX}/{analysis_id}", json=payload)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def delete(
    ctx: typer.Context,
    analysis_id: str = typer.Argument(..., help="RFM analysis id"),
    model_id: Optional[str] = typer.Option(
        None,
        "--model-id",
        help="If set, delete only this fit model rather than the whole analysis.",
    ),
) -> None:
    """Delete an RFM analysis, or one of its fit models with --model-id."""
    cfg = ctx.obj
    org = cfg.require_org()
    if model_id:
        path = f"/{org}{_PREFIX}/{analysis_id}/models/{model_id}"
    else:
        path = f"/{org}{_PREFIX}/{analysis_id}"
    with make_client(cfg) as client:
        result = client.delete(path)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def fit(
    ctx: typer.Context,
    analysis_id: str = typer.Argument(..., help="RFM analysis id"),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
    model_build_infra: Optional[str] = typer.Option(
        None,
        "--model-build-infra",
        help="Container size (s/m/l/xl/xxl) or JSON backend spec for the fit job.",
    ),
) -> None:
    """Fit (train) the RFM analysis."""
    cfg = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data, required=False) or {}
    params = {"model_build_infra": model_build_infra} if model_build_infra else None
    with make_client(cfg) as client:
        result = client.post(
            f"/{org}{_PREFIX}/{analysis_id}/fit", json=payload, params=params
        )
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command("set-active-model")
def set_active_model(
    ctx: typer.Context,
    analysis_id: str = typer.Argument(..., help="RFM analysis id"),
    model_id: Optional[str] = typer.Option(
        None,
        "--model-id",
        help="The fit run id to promote. Equivalent to --data '{\"ml_model_id\":\"...\"}'.",
    ),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
) -> None:
    """Promote a fit run to be the active model for an RFM analysis."""
    cfg = ctx.obj
    org = cfg.require_org()
    if model_id:
        if input_file or data:
            raise typer.BadParameter(
                "Use either --model-id or --input-file/--data, not both."
            )
        payload: Any = {"ml_model_id": model_id}
    else:
        payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.post(
            f"/{org}{_PREFIX}/{analysis_id}/set_active_model", json=payload
        )
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def predict(
    ctx: typer.Context,
    analysis_id: str = typer.Argument(..., help="RFM analysis id"),
    r: float = typer.Option(0.0, "--recency", "-R", help="Recency value."),
    f: float = typer.Option(0.0, "--frequency", "-F", help="Frequency value."),
    m: float = typer.Option(0.0, "--monetary", "-M", help="Monetary value."),
    ml_model_id: Optional[str] = typer.Option(
        None,
        "--ml-model-id",
        help="Specific fit run to predict against (defaults to the active model).",
    ),
) -> None:
    """Run an RFM prediction for given Recency / Frequency / Monetary values."""
    cfg = ctx.obj
    org = cfg.require_org()
    params: dict[str, str] = {"R": str(r), "F": str(f), "M": str(m)}
    if ml_model_id:
        params["ml_model_id"] = ml_model_id
    with make_client(cfg) as client:
        result = client.get(f"/{org}{_PREFIX}/{analysis_id}/predict", params=params)
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command("guess-schema")
def guess_schema(
    ctx: typer.Context,
    connection_id: str = typer.Argument(..., help="Connection id"),
    schema_name: Optional[str] = typer.Option(None, "--schema-name"),
    table_name: Optional[str] = typer.Option(None, "--table-name"),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
) -> None:
    """Ask the server to guess an RFM schema for a given connection's data."""
    cfg = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data, required=False) or {}
    params: dict[str, str] = {}
    if schema_name:
        params["schema_name"] = schema_name
    if table_name:
        params["table_name"] = table_name
    with make_client(cfg) as client:
        result = client.post(
            f"/{org}{_PREFIX}/guess_schema/{connection_id}",
            json=payload,
            params=params or None,
        )
    emit(result, cfg.output_format, quiet=cfg.quiet)
