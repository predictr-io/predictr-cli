"""Connection endpoints — manage data source connections."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from predictr_cli.client import make_client
from predictr_cli.commands._helpers import (
    ALL_PAGES_OPT,
    OUTPUT_OPT,
    PAGE_TOKEN_OPT,
    emit_list,
    resolve_output,
)
from predictr_cli.input import read_json_input
from predictr_cli.output import emit

app = typer.Typer(no_args_is_help=True, help="Manage data source connections.")


# Reusable option definitions for input flags.
_INPUT_FILE_OPT = typer.Option(
    None,
    "--input-file",
    "-f",
    help="Path to a JSON file (or '-' for stdin).",
)
_DATA_OPT = typer.Option(
    None,
    "--data",
    "-d",
    help="Inline JSON (alternative to --input-file).",
)


@app.command("list")
def list_(
    ctx: typer.Context,
    page_token: Optional[str] = PAGE_TOKEN_OPT,
    all_pages: bool = ALL_PAGES_OPT,
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """List all connections (`GET /<org>/connections`)."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        emit_list(
            client,
            f"/{org}/connections",
            cfg=cfg,
            all_pages=all_pages,
            page_token=page_token,
            output_override=output,
        )


@app.command()
def get(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id"),
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Get a single connection."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/connections/{conn_id}")
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command()
def create(
    ctx: typer.Context,
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Create a new connection from a JSON document."""
    cfg = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.post(f"/{org}/connections", json=payload)
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command()
def update(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id"),
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Update an existing connection (PATCH semantics)."""
    cfg = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.patch(f"/{org}/connections/{conn_id}", json=payload)
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command()
def delete(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id"),
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Delete a connection."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.delete(f"/{org}/connections/{conn_id}")
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command()
def test(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id"),
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Test an existing connection (`GET /<org>/connections/<id>/test`)."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/connections/{conn_id}/test")
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command("test-config")
def test_config(
    ctx: typer.Context,
    input_file: Optional[Path] = _INPUT_FILE_OPT,
    data: Optional[str] = _DATA_OPT,
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Test a connection config without saving it (`POST /<org>/connections/test`)."""
    cfg = ctx.obj
    org = cfg.require_org()
    payload = read_json_input(input_file, data)
    with make_client(cfg) as client:
        result = client.post(f"/{org}/connections/test", json=payload)
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command()
def crawl(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id"),
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Trigger a crawl to refresh table/column metadata."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.post(f"/{org}/connections/{conn_id}/crawl")
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command()
def upload(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id (must be a fileupload connection)"),
    file: Path = typer.Option(..., "--file", "-F", help="Path to the file to upload."),
    table_name: str = typer.Option(
        ..., "--table-name", "-t", help="Destination table name on the connection."
    ),
    part_number: int = typer.Option(
        1,
        "--part-number",
        help="Part number when uploading a file in chunks (1-indexed). Default 1.",
    ),
    total_parts: int = typer.Option(
        1,
        "--total-parts",
        help="Total number of parts. Default 1 (single-part upload).",
    ),
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Upload a data file (CSV) to a fileupload connection.

    For large files you can upload in parts: split locally, then call this
    command once per part with --part-number 1..N and --total-parts N.
    The server stitches them together when the final part arrives.
    """
    cfg = ctx.obj
    org = cfg.require_org()
    if not file.exists():
        raise typer.BadParameter(f"File not found: {file}")
    if part_number < 1 or part_number > total_parts:
        raise typer.BadParameter(
            f"--part-number must be between 1 and --total-parts ({total_parts})"
        )
    with make_client(cfg) as client:
        result = client.post_file(
            f"/{org}/connections/{conn_id}/upload",
            str(file),
            form_data={
                "table_name": table_name,
                "part_number": str(part_number),
                "total_parts": str(total_parts),
            },
        )
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command()
def tables(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id"),
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """List tables discovered on this connection."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(f"/{org}/connections/{conn_id}/tables")
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command()
def columns(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id"),
    table_name: str = typer.Option(..., "--table", "-t", help="Table name"),
    schema: str = typer.Option(..., "--schema", "-s", help="Schema name."),
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """List columns for a table on this connection."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        # `schema_name` is the canonical parameter name; mr-slate also accepts
        # the older `schema` for backward compat (see mr-slate app_connections).
        result = client.get(
            f"/{org}/connections/{conn_id}/columns",
            params={"table": table_name, "schema_name": schema},
        )
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command("table")
def table(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id"),
    table_name: str = typer.Argument(..., help="Table name"),
    schema: str = typer.Option(..., "--schema", "-s", help="Schema name."),
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Get a table's column definitions plus a row sample (combined endpoint)."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(
            f"/{org}/connections/{conn_id}/tables/{table_name}",
            params={"schema_name": schema},
        )
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)


@app.command("table-sample")
def table_sample(
    ctx: typer.Context,
    conn_id: str = typer.Argument(..., help="Connection id"),
    table_name: str = typer.Argument(..., help="Table name"),
    schema: str = typer.Option(..., "--schema", "-s", help="Schema name."),
    output: Optional[str] = OUTPUT_OPT,
) -> None:
    """Get a row sample as key-value pairs (column name → value)."""
    cfg = ctx.obj
    org = cfg.require_org()
    with make_client(cfg) as client:
        result = client.get(
            f"/{org}/connections/{conn_id}/tables/{table_name}/sample",
            params={"schema_name": schema},
        )
    emit(result, resolve_output(cfg, output), quiet=cfg.quiet)
