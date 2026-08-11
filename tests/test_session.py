"""Tests for DuckDBSession — connection, result formatting, env interpolation."""

from __future__ import annotations

from typing import Any, Generator

import duckdb
import pytest

from duckdb_mcp.session import DuckDBSession


@pytest.fixture()
def session() -> Generator[DuckDBSession, Any, None]:
    s = DuckDBSession(db_path=":memory:")
    yield s
    s.close()


def test_execute_formats_result_as_table(session: DuckDBSession) -> None:
    out = session.execute("SELECT 1 AS a, 'x' AS b")
    lines = out.splitlines()
    assert lines[0] == "a | b"
    assert lines[-1] == "1 | x"


def test_execute_empty_result(session: DuckDBSession) -> None:
    session.execute("CREATE TABLE t (id INT)")
    assert session.execute("SELECT * FROM t") == "No results"


def test_execute_renders_null(session: DuckDBSession) -> None:
    assert "NULL" in session.execute("SELECT NULL AS a")


def test_execute_error_is_returned_as_text(session: DuckDBSession) -> None:
    out = session.execute("SELECT * FROM does_not_exist")
    assert out.startswith("Error:")


def test_schema_defaults_to_main() -> None:
    s = DuckDBSession(db_path=":memory:")
    assert s.default_schema == "main"
    s.close()


def test_interpolate_env_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_KEY", "secret")
    assert DuckDBSession.interpolate_env_value("${MY_KEY}") == "secret"
    assert DuckDBSession.interpolate_env_value("a-${MY_KEY}-b") == "a-secret-b"
    assert DuckDBSession.interpolate_env_value("literal") == "literal"


def test_interpolate_unknown_var_is_empty() -> None:
    assert DuckDBSession.interpolate_env_value("${NOT_SET_XYZ}") == ""


def test_env_processed_before_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOURCE", "resolved")
    monkeypatch.setenv("TARGET", "${SOURCE}")
    s = DuckDBSession(db_path=":memory:")
    import os

    assert os.environ["TARGET"] == "resolved"
    s.close()


def test_read_only_blocks_writes(tmp_path) -> None:
    db = str(tmp_path / "ro.duckdb")
    writer = DuckDBSession(db_path=db)
    writer.execute("CREATE TABLE t (id INT)")
    writer.close()

    reader = DuckDBSession(db_path=db, read_only=True)
    assert reader.read_only is True
    assert reader.execute("SELECT * FROM t") == "No results"
    assert reader.execute("INSERT INTO t VALUES (1)").startswith("Error:")
    reader.close()


def test_init_sql_runs_on_startup(tmp_path) -> None:
    init = tmp_path / "init.sql"
    init.write_text("CREATE TABLE seeded (id INT); INSERT INTO seeded VALUES (42);")
    s = DuckDBSession(db_path=":memory:", init_sql=str(init))
    assert "42" in s.execute("SELECT id FROM seeded")
    s.close()


def test_bad_init_sql_falls_back_to_memory(tmp_path) -> None:
    init = tmp_path / "bad.sql"
    init.write_text("THIS IS NOT VALID SQL;")
    s = DuckDBSession(db_path=":memory:", init_sql=str(init))
    # Session still usable despite the broken init file.
    assert isinstance(s.conn, duckdb.DuckDBPyConnection)
    assert session_ok(s)
    s.close()


def session_ok(s: DuckDBSession) -> bool:
    return s.execute("SELECT 1 AS a").splitlines()[-1] == "1"
