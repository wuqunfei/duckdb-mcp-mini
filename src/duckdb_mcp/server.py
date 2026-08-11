"""MCP server wiring.

Tool logic lives in small handlers collected in ``_HANDLERS`` — pure and
unit-testable through :func:`dispatch_tool`. ``create_server`` then exposes each
handler as an MCP tool with a typed signature, so the client receives a proper
input schema for every tool.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

from mcp.server import MCPServer

from duckdb_mcp.auth import StaticTokenVerifier, build_auth_settings
from duckdb_mcp.session import DuckDBSession

SERVER_NAME = "duckdb-mcp-mini"

logger = logging.getLogger("duckdb_mcp")

#: A tool handler: given the session and the call arguments, return text output.
Handler = Callable[[DuckDBSession, dict], str]


def mask_environment() -> str:
    """List environment variables as ``key: value`` with values masked.

    Non-empty values are shown as ``****`` so secrets are never revealed;
    variables set to an empty string are shown as ``empty``.
    """
    if not os.environ:
        return "No environment variables set"
    return "\n".join(f"{key}: {'****' if os.environ[key] else 'empty'}" for key in sorted(os.environ))


def _execute(session: DuckDBSession, args: dict) -> str:
    """Run a write/DDL statement and return a status message (no result rows)."""
    try:
        assert session.conn is not None
        session.conn.execute(args["sql"])
        return "Executed successfully"
    except Exception as exc:  # noqa: BLE001 - surface as text, never crash
        return f"Error: {exc}"


def _load_file(session: DuckDBSession, reader: str, label: str, args: dict) -> str:
    """Load a file into a table using the given DuckDB reader function."""
    table = args.get("table_name", "data")
    sql = f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM {reader}('{args['filepath']}')"
    return f"Loaded {label} to '{table}'\n{session.execute(sql)}"


def _list_tables(session: DuckDBSession, _args: dict) -> str:
    return session.execute(f"SELECT table_name, table_schema FROM information_schema.tables WHERE table_schema = '{session.default_schema}'")


#: Single source of truth for the tool set: name -> handler.
_HANDLERS: dict[str, Handler] = {
    "query": lambda session, args: session.execute(args["sql"]),
    "execute": _execute,
    "read_csv": lambda session, args: _load_file(session, "read_csv_auto", "CSV", args),
    "read_parquet": lambda session, args: _load_file(session, "read_parquet", "Parquet", args),
    "list_catalogs": lambda session, _a: session.execute("SELECT * FROM information_schema.catalogs"),
    "list_databases": lambda session, _a: session.execute("SELECT * FROM information_schema.databases"),
    "list_schemas": lambda session, _a: session.execute("SELECT * FROM information_schema.schemata"),
    "list_tables": _list_tables,
    "list_columns": lambda session, args: session.execute(f"DESCRIBE {args['table_name']}"),
    "list_extensions": lambda session, _a: session.execute("SELECT extension_name FROM duckdb_extensions() WHERE loaded"),
    "list_environments": lambda _session, _a: mask_environment(),
    "check_version": lambda session, _a: session.execute("SELECT version()"),
}

#: Canonical tool inventory, derived from the handler registry.
TOOL_NAMES: list[str] = list(_HANDLERS)


def dispatch_tool(session: DuckDBSession, name: str, arguments: dict) -> str:
    """Execute the named tool against ``session`` and return its text result."""
    logger.debug("tool request: %s args=%r", name, arguments)
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"Unknown tool: {name}"
    return handler(session, arguments)


def create_server(session: DuckDBSession, version: str = "", auth_token: str | None = None, base_url: str | None = None) -> MCPServer:
    """Build the :class:`MCPServer`, exposing every handler as a typed MCP tool.

    If ``auth_token`` is given, the HTTP transport requires an
    ``Authorization: Bearer <auth_token>`` header (``base_url`` must be the
    server's own ``http://host:port``).
    """
    auth_kwargs: dict = {}
    if auth_token:
        if not base_url:
            raise ValueError("base_url is required when auth_token is set")
        auth_kwargs = {"token_verifier": StaticTokenVerifier(auth_token), "auth": build_auth_settings(base_url)}

    server: MCPServer = MCPServer(SERVER_NAME, version=version, **auth_kwargs)

    @server.tool()
    def query(sql: str) -> str:
        """Execute a SQL SELECT query and return the results."""
        return dispatch_tool(session, "query", {"sql": sql})

    @server.tool()
    def execute(sql: str) -> str:
        """Execute a SQL statement (INSERT, UPDATE, DELETE, CREATE, ...) without returning rows."""
        return dispatch_tool(session, "execute", {"sql": sql})

    @server.tool()
    def read_csv(filepath: str, table_name: str = "data") -> str:
        """Read a CSV file into a table."""
        return dispatch_tool(session, "read_csv", {"filepath": filepath, "table_name": table_name})

    @server.tool()
    def read_parquet(filepath: str, table_name: str = "data") -> str:
        """Read a Parquet file into a table."""
        return dispatch_tool(session, "read_parquet", {"filepath": filepath, "table_name": table_name})

    @server.tool()
    def list_catalogs() -> str:
        """List all catalogs."""
        return dispatch_tool(session, "list_catalogs", {})

    @server.tool()
    def list_databases() -> str:
        """List all databases."""
        return dispatch_tool(session, "list_databases", {})

    @server.tool()
    def list_schemas() -> str:
        """List all schemas."""
        return dispatch_tool(session, "list_schemas", {})

    @server.tool()
    def list_tables() -> str:
        """List all tables in the current schema."""
        return dispatch_tool(session, "list_tables", {})

    @server.tool()
    def list_columns(table_name: str) -> str:
        """List the columns of a table."""
        return dispatch_tool(session, "list_columns", {"table_name": table_name})

    @server.tool()
    def list_extensions() -> str:
        """List loaded extensions."""
        return dispatch_tool(session, "list_extensions", {})

    @server.tool()
    def list_environments() -> str:
        """List environment variables as key: value, with values masked (**** / empty)."""
        return dispatch_tool(session, "list_environments", {})

    @server.tool()
    def check_version() -> str:
        """Check the DuckDB version."""
        return dispatch_tool(session, "check_version", {})

    return server
