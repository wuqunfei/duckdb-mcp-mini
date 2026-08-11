"""Tests for CLI argument parsing and environment helpers."""

from __future__ import annotations

import pytest

from duckdb_mcp.cli import env_bool, parse_args


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "Yes", "on", " on "])
def test_env_bool_truthy(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("FLAG", value)
    assert env_bool("FLAG") is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "nonsense"])
def test_env_bool_falsey(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("FLAG", value)
    assert env_bool("FLAG") is False


def test_env_bool_absent_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLAG", raising=False)
    assert env_bool("FLAG") is False
    assert env_bool("FLAG", default=True) is True


def test_parse_args_defaults() -> None:
    args = parse_args([])
    assert args.read_only is False
    assert args.allow_unsigned_extensions is False
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_parse_args_flags() -> None:
    args = parse_args(["--read-only", "--allow-unsigned-extensions"])
    assert args.read_only is True
    assert args.allow_unsigned_extensions is True


def test_parse_args_transport() -> None:
    args = parse_args(["--transport", "http", "--host", "0.0.0.0", "--port", "9001"])
    assert args.transport == "http"
    assert args.host == "0.0.0.0"
    assert args.port == 9001


@pytest.mark.parametrize("transport", ["sse", "grpc"])
def test_parse_args_rejects_unknown_transport(transport: str) -> None:
    with pytest.raises(SystemExit):
        parse_args(["--transport", transport])
