<div align="center">

# 🦆 DuckDB MCP Server

### Give your AI assistant a blazing-fast, persistent SQL engine.

A minimal [**Model Context Protocol**](https://modelcontextprotocol.io) server that plugs [DuckDB](https://duckdb.org) straight into Claude — query CSVs, Parquet, and cloud data in plain language, at in-process speed.

[![CI](https://github.com/wuqunfei/duckdb-mcp-mini/actions/workflows/ci.yml/badge.svg)](https://github.com/wuqunfei/duckdb-mcp-mini/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-3776AB?logo=python&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-1.5.2-FFF000?logo=duckdb&logoColor=black)
![MCP](https://img.shields.io/badge/MCP-2.0-6E56CF)
![Code style](https://img.shields.io/badge/code%20style-black-000000)
![License](https://img.shields.io/badge/license-MIT-3DA639)

**⚡ ~10 ms / query · 🪶 2 runtime deps · 🧰 12 tools · 🔒 read-only & secret-safe**

</div>

---

## ✨ Why this one?

| | |
|---|---|
| ⚡ **Fast** | One persistent connection for the whole session — no subprocess spawn, no reconnect. ~10 ms per query. |
| 🪶 **Tiny** | A focused `src/` package, just **two** runtime dependencies (`duckdb`, `mcp`). No bloat, no magic. |
| 🧰 **Complete** | 12 tools covering query, write, CSV/Parquet loading, and full catalog/schema/table introspection. |
| 🔒 **Safe by default** | Engine-enforced `--read-only` mode, plus a `list_environments` tool that **masks every secret** (`****`). |
| ☁️ **Cloud-ready** | Query `s3://` Parquet directly, with `${VAR}` interpolation to keep credentials out of config files. |
| 🧩 **Extensible** | Opt-in unsigned/community extensions (e.g. TA-Lib) via a single flag or env var. |
| 🔌 **Local or remote** | Run over **stdio** (Claude Desktop) or **streamable HTTP** — one `--transport` flag. |
| 🔑 **Token auth** | Protect the HTTP transport with a bearer token from a single env var. |
| ✅ **Trustworthy** | Fully typed, linted, and tested — CI runs black + ruff + mypy + pytest on Python 3.12 & 3.13. |

---

## 🚀 Quick start

**1. Run it — no install needed** (via [uv](https://docs.astral.sh/uv/)):

```bash
uvx --from git+https://github.com/wuqunfei/duckdb-mcp-mini duckdb-mcp --db :memory:
```

**2. Point Claude Desktop at it** — add this to `claude_desktop_config.json` and restart Claude:

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

**3. Ask away** 💬

> *"Load `~/data/sales.csv` and show me total revenue by region."*

That's it. Tools are available immediately. 🎉

---

## 📦 Install

```bash
pip install .            # from a clone, into the current environment
pip install -e ".[dev]"  # for development (editable + dev tools)
```

Or run straight from Git without installing:

```bash
uvx --from git+https://github.com/wuqunfei/duckdb-mcp-mini duckdb-mcp --db :memory:
```

> ℹ️ This package is **not published to PyPI** — install from source or run from Git as shown above.

**Requirements:** 🐍 Python 3.11–3.14 · 🦆 DuckDB 1.5.2 (pinned in `pyproject.toml`, easy to change) · 🔌 MCP SDK 2.0.0+

---

## 🏃 Run

The installed console script is `duckdb-mcp`. It speaks MCP over **stdio**, so you'll normally launch it from an MCP client — but you can start it directly too:

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
| `--allow-unsigned-extensions` | Allow unsigned/community extensions (default: off; env: `ALLOW_UNSIGNED_EXTENSIONS`) |
| `--transport` | `stdio` (default) or `http` (streamable HTTP) |
| `--host` | Bind host for the `http` transport (default: `127.0.0.1`) |
| `--port` | Bind port for the `http` transport (default: `8000`) |

### 🔒 Read-only mode

`--read-only` opens the connection via DuckDB's own read-only flag, so writes are blocked at the **engine level** (not by inspecting SQL):

- ✅ `SELECT` works normally
- 🚫 `INSERT` / `UPDATE` / `DELETE` / `CREATE` / `DROP` are rejected by DuckDB
- 💡 Perfect for shared analytics/reporting databases where accidental writes must be impossible

---

## 🔌 Transports

The server speaks two MCP transports — pick with `--transport`:

| Transport | Flag | Use it for |
|-----------|------|-----------|
| **stdio** (default) | `--transport stdio` | Local clients that launch the process, e.g. Claude Desktop |
| **streamable HTTP** | `--transport http` | Remote / networked clients — the current MCP HTTP transport (single `/mcp` endpoint) |

```bash
# stdio (default) — the process talks over stdin/stdout
duckdb-mcp --db analytics.duckdb

# streamable HTTP — serve on a network address, single endpoint
duckdb-mcp --transport http --host 0.0.0.0 --port 8000 --db analytics.duckdb
#   → endpoint:  http://<host>:8000/mcp
```

Point a network MCP client at the `/mcp` endpoint:

```json
{
  "mcpServers": {
    "duckdb": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

> 🔒 `--host` defaults to `127.0.0.1` (localhost only). Bind to `0.0.0.0` only on a trusted network, and protect it with a bearer token (below).

### 🔑 Bearer token (HTTP transport)

Set the `MCP_AUTH_TOKEN` environment variable to require an `Authorization: Bearer <token>` header on every `http` request. Requests with a missing or wrong token get **401**.

```bash
export MCP_AUTH_TOKEN="a-long-random-secret"
duckdb-mcp --transport http --host 0.0.0.0 --port 8000 --db analytics.duckdb
```

Client config:

```json
{
  "mcpServers": {
    "duckdb": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": { "Authorization": "Bearer a-long-random-secret" }
    }
  }
}
```

- 🌱 **Environment only** — the token is read from `MCP_AUTH_TOKEN`, never a CLI flag, so it stays out of `ps` and shell history.
- 🔌 **HTTP only** — the token is ignored for `stdio` (the client owns the process); setting it there prints a warning.
- ⚠️ **Access control, not identity** — every caller with the token gets full database access. It is *not* a substitute for network controls or `--read-only`; pair them.

---

## 🖥️ Configure Claude Desktop

Add one of the following to your `claude_desktop_config.json`, then restart Claude.

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

### 📍 Config file locations

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### 🔁 Multiple servers

Add more entries under `mcpServers` with distinct names (e.g. `duckdb-dev`, `duckdb-prod`), each with its own `--db`/`--schema`.

---

## ☁️ Environment variables & cloud data

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

> 🔐 Interpolation happens **before** the DuckDB connection is opened, so credentials are ready in time for connection setup and any `--init-sql`. Use the `list_environments` tool to confirm what's set — values are always masked.

---

## 🧩 Community & unsigned extensions

DuckDB only loads **signed** extensions by default. To use community or self-hosted extensions, enable unsigned extensions with the `--allow-unsigned-extensions` flag **or** the `ALLOW_UNSIGNED_EXTENSIONS` environment variable (default: off):

```bash
duckdb-mcp --db :memory: --allow-unsigned-extensions
# or
ALLOW_UNSIGNED_EXTENSIONS=true duckdb-mcp --db :memory:
```

In a Claude Desktop config:

```json
{
  "mcpServers": {
    "duckdb": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/wuqunfei/duckdb-mcp-mini", "duckdb-mcp", "--db", ":memory:", "--allow-unsigned-extensions"]
    }
  }
}
```

The flag is applied as a **connection-time** setting, so it's already on — just `INSTALL` and `LOAD` through the `execute` tool. For example, [neuesql/atm_talib](https://github.com/neuesql/atm_talib) (TA-Lib for DuckDB):

```sql
INSTALL talib FROM 'https://neuesql.github.io/atm_talib';
LOAD talib;
```

> ⚠️ Unsigned extensions run native code with full trust. Only enable this for extensions from sources you trust.

---

## 🧰 Tools (12)

| Category | Tool | Purpose |
|----------|------|---------|
| 🔎 Core | `query` | Run a `SELECT` and return the result as a text table |
| ✍️ Core | `execute` | Run a write statement (`INSERT`/`UPDATE`/`DELETE`/`CREATE`/`DROP`); returns a status message |
| 📥 File I/O | `read_csv` | Load a CSV file into a table (`table_name` defaults to `data`) |
| 📥 File I/O | `read_parquet` | Load a Parquet file into a table (`table_name` defaults to `data`) |
| 📚 Introspection | `list_catalogs` | List catalogs |
| 📚 Introspection | `list_databases` | List databases |
| 📚 Introspection | `list_schemas` | List schemas |
| 📚 Introspection | `list_tables` | List tables in the current schema |
| 📚 Introspection | `list_columns` | Describe a table's columns |
| 📚 Introspection | `list_extensions` | List loaded extensions |
| 🔐 Introspection | `list_environments` | List environment variables as `key: value`, with values masked (`****`, or `empty` when unset) |
| 🏷️ Introspection | `check_version` | Report the DuckDB version |

**`query` vs `execute`** — `query` is for reads (fetches rows, formats a table); `execute` is for writes/DDL (runs the statement, returns `"Executed successfully"`).

---

## 🏗️ Architecture

```
launch (cli.main)
   ↓
DuckDBSession(...)                     # src/duckdb_mcp/session.py
   ├─ interpolate ${VAR} across os.environ   ← runs BEFORE connecting
   ├─ duckdb.connect(db, read_only=...)      ← one persistent connection
   └─ run --init-sql (if provided)           ← falls back to :memory: on error
   ↓
create_server(session)                 # src/duckdb_mcp/server.py
   └─ registers 12 tools on an mcp MCPServer; each calls dispatch_tool()
   ↓
_serve(session, transport=...)         # src/duckdb_mcp/cli.py
   └─ run_stdio_async() | run_streamable_http_async()
```

- 🧩 `session.py` holds `DuckDBSession` with **no MCP imports**, so the connection/formatting logic is unit-testable with only `duckdb`.
- 🗂️ `server.py` holds the `_HANDLERS` registry (single source of truth for the tool set) plus `dispatch_tool()` and the thin typed MCP registrations.
- 🎛️ `cli.py` parses args, builds the session, and serves.

**Good to know:**
- 🛟 If connecting to `--db` (or running `--init-sql`) fails, the session degrades to an in-memory read-write connection rather than crashing.
- ⚠️ SQL is f-string interpolated (table names, filepaths). This is intentional for a local single-user tool — inputs are **not** sanitized.

---

## 🛠️ Development

```bash
pip install -e ".[dev]"      # or: uv sync --extra dev

black --check src tests      # format (drop --check to apply)
ruff check src tests         # lint
mypy src                     # type check
pytest                       # tests

pytest tests/test_server.py::test_dispatch_query   # run a single test
```

### 📁 Project layout

```
duckdb-mcp-mini/
├── src/duckdb_mcp/
│   ├── __init__.py        # package version + DuckDBSession export
│   ├── session.py         # persistent DuckDB session (no MCP deps)
│   ├── server.py          # tool registry + dispatch + MCP server wiring
│   └── cli.py             # argument parsing + entrypoint
├── tests/                 # pytest suite
├── .github/workflows/
│   ├── ci.yml             # lint + type + test on py3.11–3.14
│   └── release.yml        # build on tag (PyPI publish disabled)
├── pyproject.toml
├── LICENSE
└── README.md
```

### 🔄 CI / CD

- **CI** (`.github/workflows/ci.yml`) runs black, ruff, mypy, and pytest on Python 3.11, 3.12, 3.13, and 3.14 for every push/PR to `main`, and checks that `duckdb-mcp --help` works.
- **CD** (`.github/workflows/release.yml`) builds the sdist/wheel on a `v*` tag and attaches them to the GitHub Release. **PyPI publishing is intentionally disabled** — the `publish-pypi` job is gated behind `if: false`; see the comments in that file to enable it later.

### 🤝 Contributing

Issues and PRs are welcome! Please keep the footprint small (the minimalism is a feature 🪶), and make sure `black` / `ruff` / `mypy` / `pytest` all pass before opening a PR.

---

<div align="center">

Built with 🦆 + 🔌 · Licensed under [MIT](./LICENSE)

</div>
