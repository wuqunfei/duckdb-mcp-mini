"""Tests for the static bearer-token verifier and auth settings."""

from __future__ import annotations

import pytest

from duckdb_mcp.auth import StaticTokenVerifier, build_auth_settings
from duckdb_mcp.server import create_server
from duckdb_mcp.session import DuckDBSession


def test_build_auth_settings_uses_base_url() -> None:
    settings = build_auth_settings("http://127.0.0.1:8000")
    assert str(settings.issuer_url).rstrip("/") == "http://127.0.0.1:8000"
    assert str(settings.resource_server_url).rstrip("/") == "http://127.0.0.1:8000"


def test_verifier_accepts_matching_token() -> None:
    import asyncio

    v = StaticTokenVerifier("s3cret")
    assert asyncio.run(v.verify_token("s3cret")) is not None


def test_verifier_rejects_wrong_token() -> None:
    import asyncio

    v = StaticTokenVerifier("s3cret")
    assert asyncio.run(v.verify_token("nope")) is None
    assert asyncio.run(v.verify_token("")) is None


def test_create_server_requires_base_url_with_token() -> None:
    s = DuckDBSession(db_path=":memory:")
    with pytest.raises(ValueError):
        create_server(s, auth_token="s3cret")  # base_url missing
    s.close()


def test_create_server_with_auth_ok() -> None:
    s = DuckDBSession(db_path=":memory:")
    server = create_server(s, auth_token="s3cret", base_url="http://127.0.0.1:8000")
    assert server.name == "duckdb-mcp-mini"
    s.close()
