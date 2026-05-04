"""Tests for JSON input handling (file / stdin / inline)."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
import typer

from pebbles.input import read_json_input


def test_read_from_file(tmp_path: Path):
    p = tmp_path / "payload.json"
    p.write_text('{"a": 1}')
    assert read_json_input(p, None) == {"a": 1}


def test_read_inline_data():
    assert read_json_input(None, '{"b": 2}') == {"b": 2}


def test_stdin_via_dash(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"c": 3}'))
    assert read_json_input(Path("-"), None) == {"c": 3}


def test_both_inputs_rejects():
    with pytest.raises(typer.BadParameter, match="only one of"):
        read_json_input(Path("/tmp/x"), '{"a": 1}')


def test_no_input_when_required():
    with pytest.raises(typer.BadParameter, match="Missing input"):
        read_json_input(None, None)


def test_no_input_when_optional_returns_none():
    assert read_json_input(None, None, required=False) is None


def test_invalid_json_rejects():
    with pytest.raises(typer.BadParameter, match="Invalid JSON"):
        read_json_input(None, "{not valid")
