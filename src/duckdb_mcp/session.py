"""Persistent DuckDB session used by the MCP server.

Kept free of any MCP imports so the core query/connection logic can be unit
tested with only ``duckdb`` installed.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import duckdb

# Matches ${VAR_NAME} references for environment-variable interpolation.
_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class DuckDBSession:
    """A long-lived DuckDB connection shared across every tool call.

    The connection is opened once in :meth:`__init__` and stays open for the
    lifetime of the process, which is what makes per-query latency low (no
    subprocess spawn, no reconnect).
    """

    def __init__(
        self,
        db_path: str | None = None,
        schema: str | None = None,
        init_sql: str | None = None,
        read_only: bool = False,
    ) -> None:
        self.conn: duckdb.DuckDBPyConnection | None = None
        self.default_database = db_path or ":memory:"
        self.default_schema = schema or "main"
        self.init_sql_file = init_sql
        self.read_only = read_only

        # Interpolate ${VAR} references in the environment BEFORE connecting, so
        # credentials (e.g. S3 keys) are resolved by the time DuckDB connects.
        self._process_environment_variables()

        self.initialize_session()

    def _process_environment_variables(self) -> None:
        """Expand ``${VAR_NAME}`` references throughout ``os.environ`` in place."""
        for key, value in list(os.environ.items()):
            if isinstance(value, str):
                os.environ[key] = self.interpolate_env_value(value)

    @staticmethod
    def interpolate_env_value(value: str) -> str:
        """Replace every ``${VAR_NAME}`` in ``value`` with ``os.environ[VAR_NAME]``.

        Unknown variables expand to an empty string. Non-reference text is
        returned unchanged.

        Examples:
            ``"${AWS_ACCESS_KEY_ID}"`` -> value from ``os.environ``
            ``"my-bucket"`` -> ``"my-bucket"``
            ``"prefix-${ENV_VAR}-suffix"`` -> ``"prefix-value-suffix"``
        """
        return _ENV_VAR_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), value)

    def initialize_session(self) -> None:
        """Open the persistent connection and run the optional init SQL.

        On any failure (bad path, invalid init SQL, ...) the session degrades to
        an in-memory read-write connection instead of crashing the server.
        """
        try:
            self.conn = duckdb.connect(self.default_database, read_only=self.read_only)

            if self.default_schema != "main":
                self.conn.execute(f"SET search_path TO {self.default_schema}")

            if self.init_sql_file and Path(self.init_sql_file).exists():
                init_sql = Path(self.init_sql_file).read_text()
                if init_sql.strip():
                    self.conn.execute(init_sql)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash
            print(f"Error initializing session: {exc}", file=sys.stderr)
            self.conn = duckdb.connect(":memory:", read_only=False)

    def execute(self, sql: str) -> str:
        """Run ``sql`` and return the result as a pipe-delimited text table.

        Errors are caught and returned as ``"Error: ..."`` text rather than
        raised, so a bad query never tears down the session.
        """
        try:
            assert self.conn is not None
            result = self.conn.execute(sql).fetchall()
            if not result:
                return "No results"

            columns = self.conn.description
            if not columns:
                return str(result)

            col_names = [col[0] for col in columns]
            lines = [" | ".join(col_names)]
            lines.append("-" * (sum(len(name) for name in col_names) + len(col_names) * 2))
            for row in result:
                lines.append(" | ".join(str(val) if val is not None else "NULL" for val in row))
            return "\n".join(lines)
        except Exception as exc:  # noqa: BLE001 - surface errors to the caller as text
            return f"Error: {exc}"

    def close(self) -> None:
        """Close the underlying connection if it is open."""
        if self.conn:
            self.conn.close()
            self.conn = None
