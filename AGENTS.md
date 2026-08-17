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
  note viewer/editor, force-directed graph, cited chat, tags, vault workspace,
  saved searches, flashcards, and watcher status) with its own
  `package.json`, Vitest component/page tests, and a Playwright smoke spec. It is
  a separate toolchain from the Python gate — see `apps/web/README.md`.

## Commands

Run from the project root:

```bash
make install      # python -m pip install -e ".[dev]"
make dev          # python -m apps.api.src.main  (FastAPI on :8000)
make test         # pytest
make lint         # ruff check .
make format       # ruff format .
make typecheck    # pyright apps/api/src/
make docker-up    # optional: docker compose up -d  (Postgres + Redis)
make demo         # python examples/run_demo.py
alembic upgrade head   # apply DB migrations (only needed for persistence)
```

## Module Inventory

- **`main.py`** — FastAPI app, endpoints, lifespan DB probe, middleware.
- **`engine.py`** — `KnowledgeBase` orchestration shared by API + worker.
- **`indexer.py`** — parse (docparse), chunk, extract wikilinks/tags/frontmatter.
- **`embeddings.py`** — sync facade over internal vendored embeddings (offline/real).
- **`search.py`** — keyword scorer + semantic vector retrieval.
- **`chat.py`** — RAG answer (sim/real LLM) + `CitationJudge` grounding.
- **`graph.py`** — backlinks adjacency + `{nodes, edges}` export and dangling-link metadata.
- **`store.py` / `models.py` / `db.py`** — persistence + DB-availability fallback.
- **`worker.py`** — Celery tasks (`kb.index_vault`, `kb.reindex`).
- **`config.py`** — `AppConfig` extending internal `vendor_core.config.BaseAppConfig`.
- **`events.py` / `watcher.py`** — bounded replayable SSE events and explicit polling watchers.
- **`flashcards.py`** — deterministic source-cited cards and local review scheduling.

## Internal compatibility layer

`apps/api/src/internal/vendor_core/` contains the pinned v1.3.0 closure for
`config`, `database`, `redis`, `errors`, `health`, `logging`, `llm`, `embeddings`,
`vectorstore`, `docparse`, `evaljudge` (`CitationJudge`), `tasks`, `testing`, and
transitive pricing. The repository installs without a sibling package.

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
- **Vault containment**: API indexing/editing accepts only the configured vault
  root, rejects symlink components and path escapes, and bounds text edits to
  2 MiB. `vault_id="default"` preserves legacy callers; watcher startup is always
  explicit. These local safeguards are not a hosted auth or multi-user boundary.
