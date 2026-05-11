"""Helpers for accepting complex JSON input from the user.

Three ways to pass JSON to a command:
  --input-file path.json
  --input -            (read from stdin)
  --data '<json>'      (inline)

Exactly one of these should be supplied; this module enforces that.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer


def read_json_input(
    input_file: Optional[Path],
    inline_data: Optional[str],
    *,
    required: bool = True,
) -> Optional[Any]:
    """Resolve which input source the user picked and return the parsed JSON.

    Returns None when nothing was supplied and required=False, otherwise raises
    a Typer error (which prints a friendly message and exits non-zero).
    """
    sources_used = sum(
        [
            input_file is not None,
            inline_data is not None,
        ]
    )
    # `--input-file -` is the convention for stdin.
    use_stdin = input_file is not None and str(input_file) == "-"

    if sources_used > 1:
        raise typer.BadParameter("Pass only one of --input-file or --data.")

    if sources_used == 0:
        if required:
            raise typer.BadParameter(
                "Missing input. Use --input-file <path>, --input-file - "
                "(stdin), or --data '<json>'."
            )
        return None

    if use_stdin:
        raw = sys.stdin.read()
    elif input_file is not None:
        raw = input_file.read_text()
    else:
        raw = inline_data or ""

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON input: {exc}") from exc
