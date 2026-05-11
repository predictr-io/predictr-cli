"""Meta endpoints — server info, schemas, available transformations.

These endpoints don't take an org, so they're a useful smoke test for
configuration / auth without needing PREDICTR_ORG to be set.
"""

from __future__ import annotations

import typer

from predictr_cli.client import make_client
from predictr_cli.output import emit

app = typer.Typer(no_args_is_help=True, help="Server meta info & schemas.")


@app.command()
def info(ctx: typer.Context) -> None:
    """Show backend version and meta info (`GET /meta`)."""
    cfg = ctx.obj
    with make_client(cfg) as client:
        result = client.get("/meta")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command()
def transformations(ctx: typer.Context) -> None:
    """List available dataset transformations (`GET /meta/transformations`)."""
    cfg = ctx.obj
    with make_client(cfg) as client:
        result = client.get("/meta/transformations")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command("schema-model")
def schema_model(ctx: typer.Context) -> None:
    """Show the JSON Schema for the model resource."""
    cfg = ctx.obj
    with make_client(cfg) as client:
        result = client.get("/meta/schema/model")
    emit(result, cfg.output_format, quiet=cfg.quiet)


@app.command("schema-dataset")
def schema_dataset(ctx: typer.Context) -> None:
    """Show the JSON Schema for the dataset resource."""
    cfg = ctx.obj
    with make_client(cfg) as client:
        result = client.get("/meta/schema/dataset")
    emit(result, cfg.output_format, quiet=cfg.quiet)
