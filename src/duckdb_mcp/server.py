"""MCP server wiring.

The query logic lives in :func:`dispatch_tool` (pure, easily unit tested); the
MCP-facing layer is a set of thin decorated tool functions registered on an
:class:`~mcp.server.MCPServer`.
"""

from __future__ import annotations

from mcp.server import MCPServer

from duckdb_mcp.session import DuckDBSession

SERVER_NAME = "duckdb-mcp-minimal"

# Every tool the server exposes. Keep in sync with the registrations in
# ``create_server`` and the branches in ``dispatch_tool``.
TOOL_NAMES: list[str] = [
    "query",
    "execute",
    "read_csv",
    "read_parquet",
    "list_catalogs",
    "list_databases",
    "list_schemas",
    "list_tables",
    "list_columns",
    "list_extensions",
    "check_version",
]


def dispatch_tool(session: DuckDBSession, name: str, arguments: dict) -> str:
    """Execute the named tool against ``session`` and return its text result."""
    if name == "query":
        return session.execute(arguments["sql"])

    if name == "execute":
        try:
            assert session.conn is not None
            session.conn.execute(arguments["sql"])
            return "Executed successfully"
        except Exception as exc:  # noqa: BLE001
            return f"Error: {exc}"

    if name == "read_csv":
        table_name = arguments.get("table_name", "data")
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_csv_auto('{arguments['filepath']}')"
        return f"Loaded CSV to '{table_name}'\n{session.execute(sql)}"

    if name == "read_parquet":
        table_name = arguments.get("table_name", "data")
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_parquet('{arguments['filepath']}')"
        return f"Loaded Parquet to '{table_name}'\n{session.execute(sql)}"

    if name == "list_catalogs":
        return session.execute("SELECT * FROM information_schema.catalogs")

    if name == "list_databases":
        return session.execute("SELECT * FROM information_schema.databases")

    if name == "list_schemas":
        return session.execute("SELECT * FROM information_schema.schemata")

    if name == "list_tables":
        return session.execute("SELECT table_name, table_schema FROM information_schema.tables " f"WHERE table_schema = '{session.default_schema}'")

    if name == "list_columns":
        return session.execute(f"DESCRIBE {arguments['table_name']}")

    if name == "list_extensions":
        return session.execute("SELECT extension_name FROM duckdb_extensions() WHERE loaded")

    if name == "check_version":
        return session.execute("SELECT version()")

    return f"Unknown tool: {name}"


def create_server(session: DuckDBSession, version: str = "") -> MCPServer:
    """Build the :class:`MCPServer` with every tool bound to ``session``."""
    server: MCPServer = MCPServer(SERVER_NAME, version=version)

    @server.tool()
    def query(sql: str) -> str:
        """Execute SQL SELECT query and return results."""
        return dispatch_tool(session, "query", {"sql": sql})

    @server.tool()
    def execute(sql: str) -> str:
        """Execute SQL statement (INSERT, UPDATE, DELETE, CREATE, ...) without returning results."""
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
    def check_version() -> str:
        """Check the DuckDB version."""
        return dispatch_tool(session, "check_version", {})

    return server
