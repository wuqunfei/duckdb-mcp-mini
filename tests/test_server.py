"""Tests for tool registration and the dispatch layer."""

from __future__ import annotations

import os
from typing import Any, Generator

import pytest

from duckdb_mcp.server import SERVER_NAME, TOOL_NAMES, create_server, dispatch_tool
from duckdb_mcp.session import DuckDBSession


@pytest.fixture()
def session() -> Generator[DuckDBSession, Any, None]:
    s = DuckDBSession(db_path=":memory:")
    yield s
    s.close()


def test_twelve_tools_registered() -> None:
    assert len(TOOL_NAMES) == 12
    assert {"query", "execute", "read_csv", "read_parquet", "list_environments"} <= set(TOOL_NAMES)


def test_no_tool_falls_through_to_unknown(session: DuckDBSession) -> None:
    session.execute("CREATE TABLE IF NOT EXISTS t (id INT)")
    args_by_tool = {
        "query": {"sql": "SELECT 1"},
        "execute": {"sql": "SELECT 1"},
        "list_columns": {"table_name": "t"},
    }
    for name in TOOL_NAMES:
        if name in ("read_csv", "read_parquet"):
            continue  # need a real file; covered separately
        out = dispatch_tool(session, name, args_by_tool.get(name, {}))
        assert not out.startswith("Unknown tool"), name


def test_dispatch_query(session: DuckDBSession) -> None:
    assert dispatch_tool(session, "query", {"sql": "SELECT 1 AS a"}).splitlines()[-1] == "1"


def test_dispatch_execute(session: DuckDBSession) -> None:
    assert dispatch_tool(session, "execute", {"sql": "CREATE TABLE t (id INT)"}) == "Executed successfully"


def test_dispatch_execute_error(session: DuckDBSession) -> None:
    assert dispatch_tool(session, "execute", {"sql": "NOT SQL"}).startswith("Error:")


def test_dispatch_unknown_tool(session: DuckDBSession) -> None:
    assert dispatch_tool(session, "nope", {}).startswith("Unknown tool")


def test_dispatch_logs_request_at_debug(session: DuckDBSession, caplog: pytest.LogCaptureFixture) -> None:
    import logging

    with caplog.at_level(logging.DEBUG, logger="duckdb_mcp"):
        dispatch_tool(session, "query", {"sql": "SELECT 1"})
    assert "tool request: query" in caplog.text
    assert "SELECT 1" in caplog.text


def test_read_csv_loads_table(session: DuckDBSession, tmp_path) -> None:
    csv = tmp_path / "data.csv"
    csv.write_text("id,name\n1,alice\n2,bob\n")
    out = dispatch_tool(session, "read_csv", {"filepath": str(csv), "table_name": "people"})
    assert "Loaded CSV to 'people'" in out
    assert "2" in dispatch_tool(session, "query", {"sql": "SELECT COUNT(*) FROM people"})


def test_list_environments_masks_values(session: DuckDBSession, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_SECRET", "super-secret-value")
    monkeypatch.setenv("MY_EMPTY", "")
    out = dispatch_tool(session, "list_environments", {})
    assert "MY_SECRET: ****" in out
    assert "MY_EMPTY: empty" in out
    assert "super-secret-value" not in out  # value never leaks


def test_list_environments_when_empty(session: DuckDBSession, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "environ", {})
    assert dispatch_tool(session, "list_environments", {}) == "No environment variables set"


def test_check_version(session: DuckDBSession) -> None:
    out = dispatch_tool(session, "check_version", {})
    assert not out.startswith("Error:")
    assert "v" in out.lower()


def test_create_server_smoke(session: DuckDBSession) -> None:
    server = create_server(session)
    assert server.name == SERVER_NAME
