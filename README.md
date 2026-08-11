# DuckDB MCP Server

A minimal, fast [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server for DuckDB with a persistent session.

**Small surface. 2 runtime dependencies. 11 tools. ~10 ms per query.**

- **Persistent session** — one connection stays open for the process lifetime, so there's no per-query reconnect/subprocess overhead.
- **Flexible config** — `--db`, `--schema`, `--init-sql`, `--read-only`, plus `${VAR}` environment interpolation.
- **Read-only mode** — enforced by DuckDB itself for shared/production databases.

---

## Requirements

- **Python** 3.12+
- **DuckDB** 1.5.5+
- **MCP SDK** 2.0.0+

---

## Install

```bash
# From a clone, into the current environment
pip install .

# For development (editable + dev tools)
pip install -e ".[dev]"
```

Or run without installing, straight from Git, using [uv](https://docs.astral.sh/uv/):

```bash
uvx --from git+https://github.com/wuqunfei/duckdb-mcp-mini duckdb-mcp --db :memory:
```

> This package is **not published to PyPI**. Install from source or run from Git as shown above.

---

## Run

The installed console script is `duckdb-mcp`. It speaks MCP over **stdio**, so you normally launch it from an MCP client (see below), but you can start it directly too:

```bash
duckdb-mcp                                             # in-memory, read-write
duckdb-mcp --db /path/to/analytics.duckdb --schema main
duckdb-mcp --db analytics.duckdb --init-sql init.sql
duckdb-mcp --db analytics.duckdb --read-only

python -m duckdb_mcp.cli --db :memory:                 # module form
uv run duckdb-mcp --db :memory:                        # via uv, no install
```

### CLI arguments

| Flag | Description |
|------|-------------|
| `--db`, `--database` | Database path (`:memory:` or `/path/to/db.duckdb`). Default: `:memory:` |
| `--schema` | Default schema. Default: `main` |
| `--init-sql` | Path to a SQL file executed once on startup |
| `--read-only` | Open the database read-only (default: read-write) |

### Read-only mode

`--read-only` opens the connection via DuckDB's own read-only flag, so writes are blocked at the engine level (not by inspecting SQL):

- ✅ `SELECT` works normally
- ❌ `INSERT` / `UPDATE` / `DELETE` / `CREATE` / `DROP` are rejected by DuckDB
- Useful for shared analytics/reporting databases where accidental writes must be impossible

---

## Configure Claude Desktop

Add one of the following to your `claude_desktop_config.json`, then restart Claude. A copy-paste starting point lives in [`claude_desktop_config.json`](./claude_desktop_config.json).

**Run from Git (no install):**

```json
{
  "mcpServers": {
    "duckdb": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/wuqunfei/duckdb-mcp-mini", "duckdb-mcp", "--db", ":memory:"]
    }
  }
}
```

**Run from a local clone:**

```json
{
  "mcpServers": {
    "duckdb": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/duckdb-mcp-mini", "duckdb-mcp", "--db", "/home/user/analytics.duckdb", "--schema", "main"]
    }
  }
}
```

**After `pip install .` (command on PATH):**

```json
{
  "mcpServers": {
    "duckdb": {
      "command": "duckdb-mcp",
      "args": ["--db", "/home/user/analytics.duckdb", "--read-only"]
    }
  }
}
```

### Config file locations

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### Multiple servers

Add more entries under `mcpServers` with distinct names (e.g. `duckdb-dev`, `duckdb-prod`), each with its own `--db`/`--schema`.

---

## Environment variables

Any variables set in the client's `env` block are available to DuckDB during connection (handy for S3/cloud credentials). Values support **`${VAR_NAME}` interpolation**, so you can reference the system environment instead of hardcoding secrets into the config file:

```json
{
  "mcpServers": {
    "duckdb": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/wuqunfei/duckdb-mcp-mini", "duckdb-mcp", "--db", ":memory:"],
      "env": {
        "AWS_ACCESS_KEY_ID": "${AWS_ACCESS_KEY_ID}",
        "AWS_SECRET_ACCESS_KEY": "${AWS_SECRET_ACCESS_KEY}",
        "AWS_REGION": "${AWS_REGION}",
        "S3_BUCKET": "my-data-bucket"
      }
    }
  }
}
```

Set the referenced variables in your shell first:

```bash
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-east-1"
```

Then query cloud data directly:

```sql
SELECT * FROM read_parquet('s3://my-data-bucket/data.parquet')
```

Interpolation happens **before** the DuckDB connection is opened, so credentials are ready in time for connection setup and any `--init-sql`.

---

## Tools (11)

| Category | Tool | Purpose |
|----------|------|---------|
| Core | `query` | Run a `SELECT` and return the result as a text table |
| Core | `execute` | Run a write statement (`INSERT`/`UPDATE`/`DELETE`/`CREATE`/`DROP`); returns a status message |
| File I/O | `read_csv` | Load a CSV file into a table (`table_name` defaults to `data`) |
| File I/O | `read_parquet` | Load a Parquet file into a table (`table_name` defaults to `data`) |
| Introspection | `list_catalogs` | List catalogs |
| Introspection | `list_databases` | List databases |
| Introspection | `list_schemas` | List schemas |
| Introspection | `list_tables` | List tables in the current schema |
| Introspection | `list_columns` | Describe a table's columns |
| Introspection | `list_extensions` | List loaded extensions |
| Introspection | `check_version` | Report the DuckDB version |

### `query` vs `execute`

- **`query`** is for reads — it fetches rows and formats them as a pipe-delimited table.
- **`execute`** is for writes/DDL — it runs the statement and returns `"Executed successfully"` (no rows to format).

---

## Architecture

```
launch (cli.main)
   ↓
DuckDBSession(...)                     # src/duckdb_mcp/session.py
   ├─ interpolate ${VAR} across os.environ   ← runs BEFORE connecting
   ├─ duckdb.connect(db, read_only=...)      ← one persistent connection
   └─ run --init-sql (if provided)           ← falls back to :memory: on error
   ↓
create_server(session)                 # src/duckdb_mcp/server.py
   └─ registers 11 tools on an mcp MCPServer; each calls dispatch_tool()
   ↓
server.run_stdio_async()               # serves MCP over stdio until client disconnects
```

- `session.py` holds `DuckDBSession` and has **no MCP imports**, so the connection/formatting logic is unit-testable with only `duckdb`.
- `server.py` holds the pure `dispatch_tool(session, name, args)` function plus the thin MCP tool registrations.
- `cli.py` parses args, builds the session, and serves.

**Notes worth knowing:**
- If connecting to `--db` (or running `--init-sql`) fails, the session degrades to an in-memory read-write connection rather than crashing.
- SQL is f-string interpolated (table names, filepaths). This is intentional for a local single-user tool — inputs are **not** sanitized.

---

## Development

```bash
pip install -e ".[dev]"

black --check src tests   # format (drop --check to apply)
ruff check src tests      # lint
mypy src                  # type check
pytest                    # tests

# run a single test
pytest tests/test_server.py::test_dispatch_query
```

### Project layout

```
duckdb-mcp-mini/
├── src/duckdb_mcp/
│   ├── __init__.py        # package version + DuckDBSession export
│   ├── session.py         # persistent DuckDB session (no MCP deps)
│   ├── server.py          # tool dispatch + MCP server wiring
│   └── cli.py             # argument parsing + entrypoint
├── tests/                 # pytest suite
├── .github/workflows/
│   ├── ci.yml             # lint + type + test on py3.12 / py3.13
│   └── release.yml        # build on tag (PyPI publish disabled)
├── pyproject.toml
├── claude_desktop_config.json
├── LICENSE
└── README.md
```

### CI / CD

- **CI** (`.github/workflows/ci.yml`) runs black, ruff, mypy, and pytest on Python 3.12 and 3.13 for every push/PR to `main`, and checks that `duckdb-mcp --help` works.
- **CD** (`.github/workflows/release.yml`) builds the sdist/wheel on a `v*` tag and attaches them to the GitHub Release. **PyPI publishing is intentionally disabled** — the `publish-pypi` job is gated behind `if: false`; see the comments in that file to enable it later.

### Contributing

Issues and PRs are welcome. Please keep the footprint small (the minimalism is a feature), and make sure `black`/`ruff`/`mypy`/`pytest` all pass before opening a PR.

---

## License

MIT — see [LICENSE](./LICENSE).
