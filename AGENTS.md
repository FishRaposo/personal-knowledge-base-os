# AGENTS.md — Personal Knowledge Base OS

## What This Is

An Obsidian-compatible note parsing engine and backlinks graph builder. It reads local markdown directories, parses wikilinks, and compiles network adjacency configurations.

## Layout Exception (CRITICAL)

Unlike standard workspace repos, this project uses a monorepo layout:
- **Source root**: `apps/api/src/` (NOT `src/`).
- **Tests root**: `apps/api/tests/` or `tests/`.
- **Config**: `pyproject.toml` is in the root directory, but references `apps/api/src`.

## Commands

Commands are run from the project root:

```bash
make install          # pip install -e ../shared-core && pip install -r apps/api/requirements.txt
make dev              # python apps/api/src/main.py (FastAPI on :8000)
make test             # pytest
make lint             # ruff check .
make format           # ruff format .
make typecheck        # pyright apps/api/src/
make docker-up        # docker compose up -d (Postgres + Redis)
make demo             # python examples/run_demo.py
```

## Module Inventory

- **`apps/api/src/main.py`**: API route definitions, health endpoints, and middleware.
- **`apps/api/src/indexer.py`**: Reads directories, filters `.md` files, and extracts links matching `[[Link Name]]` regex patterns.
- **`apps/api/src/graph.py`**: Compiles nodes, builds outgoing adjacency listings, and queries backlinks.

## Integrations & Secrets

- **`shared-core`**: Core database/cache models. Must be installed as editable (`-e`).
- **Input Traversal Concern**: The `path` parameter on `/notes/index` receives arbitrary directories. Check security boundaries before updating code.
