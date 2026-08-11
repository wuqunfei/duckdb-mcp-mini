"""Command-line entrypoint for the DuckDB MCP server."""

from __future__ import annotations

import argparse
import asyncio
import sys

from duckdb_mcp import __version__
from duckdb_mcp.server import create_server
from duckdb_mcp.session import DuckDBSession

_EPILOG = """\
Examples:
  duckdb-mcp
  duckdb-mcp --db /path/to/db.duckdb
  duckdb-mcp --db :memory: --schema main
  duckdb-mcp --db analytics.duckdb --init-sql init.sql --read-only
"""


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
    return parser.parse_args(argv)


async def _serve(session: DuckDBSession) -> None:
    """Serve the MCP protocol over stdio until the client disconnects."""
    server = create_server(session, version=__version__)
    await server.run_stdio_async()


def main(argv: list[str] | None = None) -> int:
    """Console-script entrypoint: parse args, open the session, serve."""
    args = parse_args(argv)
    session: DuckDBSession | None = None
    try:
        session = DuckDBSession(
            db_path=args.database,
            schema=args.schema,
            init_sql=args.init_sql,
            read_only=args.read_only,
        )
        asyncio.run(_serve(session))
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
