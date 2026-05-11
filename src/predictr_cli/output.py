"""Output formatting helpers.

Default to JSON for pipe-friendliness; offer YAML and table formats
when humans (rather than scripts) are looking at the result.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import yaml
from rich.console import Console
from rich.json import JSON as RichJSON
from rich.table import Table

# Two consoles: one for normal output, one specifically for stderr (errors,
# logs). Rich auto-detects TTY and disables colour for non-TTY output.
_stdout = Console()
_stderr = Console(stderr=True)


def emit(value: Any, output_format: str = "json", *, quiet: bool = False) -> None:
    """Print a result in the chosen format. Suppressed entirely if quiet."""
    if quiet or value is None:
        return

    fmt = (output_format or "json").lower()
    if fmt == "json":
        _emit_json(value)
    elif fmt == "yaml":
        _stdout.print(yaml.safe_dump(value, sort_keys=False).rstrip())
    elif fmt == "table":
        _emit_table(value)
    else:
        # Unknown format → fall back to JSON rather than crashing.
        _emit_json(value)


def emit_error(message: str) -> None:
    """Print an error message to stderr in red (when colour is supported)."""
    _stderr.print(f"[bold red]error:[/] {message}")


def _emit_json(value: Any) -> None:
    """JSON output: pretty when a TTY is attached, raw when piped."""
    payload = json.dumps(value, indent=2, default=str)
    if _stdout.is_terminal:
        _stdout.print(RichJSON(payload))
    else:
        # Plain stdout for piping; no colour, no Rich line-wrap.
        sys.stdout.write(payload + "\n")


def _emit_table(value: Any) -> None:
    """Render a list-of-dicts as a Rich table; fall back to JSON otherwise."""
    if not isinstance(value, list) or not value or not isinstance(value[0], dict):
        _emit_json(value)
        return

    columns: list[str] = []
    for item in value:
        for key in item.keys():
            if key not in columns:
                columns.append(key)

    table = Table(show_header=True, header_style="bold")
    for column in columns:
        table.add_column(column)
    for item in value:
        table.add_row(*[_to_cell(item.get(c)) for c in columns])

    _stdout.print(table)


def _to_cell(value: Any) -> str:
    """Render a single cell for a table; nested values become JSON."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)
