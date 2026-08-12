"""DuckDB MCP Server — minimal, fast MCP server for DuckDB with persistent sessions."""

from duckdb_mcp.session import DuckDBSession

__version__ = "0.2.1"
__all__ = ["DuckDBSession", "__version__"]
