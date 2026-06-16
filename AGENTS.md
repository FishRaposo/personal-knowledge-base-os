# AGENTS.md — Personal Knowledge Base OS

## What This Is

A local-first knowledge base API. It ingests a markdown vault, parses
Obsidian-style `[[wikilinks]]` into a bidirectional backlinks graph, supports
keyword + semantic search, and answers questions over the notes with grounded
citations. Offline-first: runs and tests with no database, no API key, and no
network; upgrades to PostgreSQL + pgvector + real LLM/embeddings when configured.

## Layout Exception (CRITICAL)

Unlike standard workspace repos, this project uses a monorepo layout:
- **Python package root**: `apps/api/src/` (NOT `src/`). Modules are imported via
  the `apps.api.src` package (e.g. `from apps.api.src.engine import KnowledgeBase`),
  and internally use relative imports (`from .chat import ...`). Tests and the demo
  add the **project root** to `sys.path` so `apps.api.src` resolves as a package.
- **Tests root**: `tests/`.
- **Config**: `pyproject.toml` / `alembic.ini` live in the project root and point
  back at `apps/api/src`.
- **Web frontend**: `apps/web/` is a built, tested Next.js 14 dashboard (search,
  note viewer, force-directed graph, cited chat, tags) with its own
  `package.json`, Vitest component/page tests, and a Playwright smoke spec. It is
  a separate toolchain from the Python gate — see `apps/web/README.md`.

## Commands

Run from the project root:

```bash
make install      # pip install -e ../shared-core && pip install -r requirements.txt
make dev          # python apps/api/src/main.py  (FastAPI on :8000)
make test         # pytest
make lint         # ruff check .
make format       # ruff format .
make typecheck    # pyright apps/api/src/
make docker-up    # docker compose up -d  (Postgres + Redis)
make demo         # python examples/run_demo.py
alembic upgrade head   # apply DB migrations (only needed for persistence)
```

## Module Inventory

- **`main.py`** — FastAPI app, endpoints, lifespan DB probe, middleware.
- **`engine.py`** — `KnowledgeBase` orchestration shared by API + worker.
- **`indexer.py`** — parse (docparse), chunk, extract wikilinks/tags/frontmatter.
- **`embeddings.py`** — sync facade over `shared_core.embeddings` (offline/real).
- **`search.py`** — keyword scorer + semantic vector retrieval.
- **`chat.py`** — RAG answer (sim/real LLM) + `CitationJudge` grounding.
- **`graph.py`** — backlinks adjacency + `{nodes, edges}` export.
- **`store.py` / `models.py` / `db.py`** — persistence + DB-availability fallback.
- **`worker.py`** — Celery tasks (`kb.index_vault`, `kb.reindex`).
- **`config.py`** — `AppConfig` extending `shared_core.config.BaseAppConfig`.

## shared_core Usage

`config`, `database`, `redis`, `errors`, `health`, `logging`, `llm`, `embeddings`,
`vectorstore`, `docparse`, `evaljudge` (`CitationJudge`), `tasks`, `testing`
(`MockDatabase`). Must be installed editable (`-e ../shared-core`).

## Conventions & Gotchas

- **Offline-first**: never require keys/DB/network for tests or the demo. Use
  `get_embedding_provider(offline=True)` / `get_vector_store(offline=True)` and the
  simulated chat path by default.
- **Determinism**: offline embeddings and the simulated chat answer are
  deterministic; `tests/test_golden.py` pins them — update golden values
  deliberately if a scorer/provider changes.
- **`/health` is slow offline** (real socket connects); API tests patch
  `db_manager` / `redis_manager` and use a plain `TestClient` (no lifespan) to stay
  fast and in-memory.
- **Input traversal**: `/notes/index` takes an arbitrary `path`. Sandbox hardening
  is documented in `docs/security.md`; enforce it before untrusted exposure.
