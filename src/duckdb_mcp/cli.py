"""Command-line entrypoint for the DuckDB MCP server."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from duckdb_mcp import __version__
from duckdb_mcp.server import create_server
from duckdb_mcp.session import DuckDBSession

_EPILOG = """\
Examples:
  duckdb-mcp                                          # stdio (default)
  duckdb-mcp --db /path/to/db.duckdb
  duckdb-mcp --db :memory: --schema main
  duckdb-mcp --db analytics.duckdb --init-sql init.sql --read-only
  duckdb-mcp --allow-unsigned-extensions              # or: ALLOW_UNSIGNED_EXTENSIONS=true
  duckdb-mcp --transport sse --host 0.0.0.0 --port 8000    # HTTP + SSE
  duckdb-mcp --transport http --port 8000                  # streamable HTTP
"""

_TRUTHY = {"1", "true", "yes", "on"}


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean-ish environment variable (1/true/yes/on, case-insensitive)."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUTHY


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="duckdb-mcp",
        description="DuckDB MCP Server - persistent session",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOG,
    )
    parser.add_argument("--db", "--database", dest="database", help="Default database path")
    parser.add_argument("--schema", help="Default schema (default: main)")
    parser.add_argument("--init-sql", dest="init_sql", help="Path to init SQL file")
    parser.add_argument(
        "--read-only",
        action="store_true",
        default=False,
        help="Open database in read-only mode (default: read-write)",
    )
    parser.add_argument(
        "--allow-unsigned-extensions",
        action="store_true",
        default=False,
        help="Allow loading unsigned/community DuckDB extensions (default: false; env: ALLOW_UNSIGNED_EXTENSIONS)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport: stdio (default), sse (HTTP+SSE), or http (streamable HTTP)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host for sse/http transports (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port for sse/http transports (default: 8000)")
    return parser.parse_args(argv)


async def _serve(session: DuckDBSession, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None:
    """Serve the MCP protocol over the chosen transport until the client disconnects."""
    server = create_server(session, version=__version__)
    if transport == "sse":
        await server.run_sse_async(host=host, port=port)
    elif transport == "http":
        await server.run_streamable_http_async(host=host, port=port)
    else:
        await server.run_stdio_async()


def main(argv: list[str] | None = None) -> int:
    """Console-script entrypoint: parse args, open the session, serve."""
    args = parse_args(argv)
    session: DuckDBSession | None = None
    try:
        # Enabled by either the CLI flag or the ALLOW_UNSIGNED_EXTENSIONS env var.
        allow_unsigned = args.allow_unsigned_extensions or env_bool("ALLOW_UNSIGNED_EXTENSIONS")
        session = DuckDBSession(
            db_path=args.database,
            schema=args.schema,
            init_sql=args.init_sql,
            read_only=args.read_only,
            allow_unsigned_extensions=allow_unsigned,
        )
        asyncio.run(_serve(session, transport=args.transport, host=args.host, port=args.port))
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
