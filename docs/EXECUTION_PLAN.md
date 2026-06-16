# Execution Plan — Personal Knowledge Base OS

This document records how the MVP was taken from ~60-75% (real core logic, a demo,
docs, some tests) to a fully implemented, tested, and documented state. It is the
"what was actually executed" companion to `implementation_plan.md`.

---

## Starting point

The repo already had: a regex wikilink indexer, an in-memory backlinks graph, a
keyword scorer, a template chat function, a `MockEmbeddingGenerator`, a Celery
scaffold, and 16 passing tests (indexer/graph + two API smoke tests). Search was
keyword-only (`semantic_search` was a stub), there was no persistence, no Alembic,
no embeddings beyond the mock, and the API exposed only index/search/chat/backlinks.

---

## Work executed

### Retrieval & AI logic (stubs → real)
- **Embeddings**: Replaced `MockEmbeddingGenerator` with `EmbeddingGenerator`, a
  sync facade over `shared_core.embeddings` — offline `HashFallbackProvider` by
  default, OpenAI when `OPENAI_API_KEY` is set. No torch / sentence-transformers.
- **Semantic search**: Implemented real vector retrieval over
  `shared_core.vectorstore` (`InMemoryVectorStore` offline, `PgVectorStore` when a
  DB is configured). Chunk hits roll up to parent notes with the best snippet.
  Added a `hybrid` mode merging keyword + semantic.
- **Ingestion**: Rebuilt the indexer on `shared_core.docparse` (`MarkdownParser` +
  `chunk_text`). Added YAML frontmatter parsing, `#hashtag` + frontmatter tag
  extraction, content hashing, recursive traversal, and per-note chunking — while
  keeping wikilink extraction (now alias- and slug-aware).
- **Chat with citations**: Real RAG — retrieve chunks, build a grounded prompt,
  answer with a deterministic simulation offline or a real LLM via
  `shared_core.llm.LLMClientFactory` when keyed (with graceful fallback). Citation
  grounding is *scored* with `shared_core.evaljudge.CitationJudge`.

### Persistence (new)
- `models.py` (`Note`, `NoteChunk`), `store.py` (`InMemoryNoteStore` +
  `DatabaseNoteStore`), and `db.py` (fast TCP probe + `SELECT 1`, in-memory
  fallback) — DB persistence by default with graceful fallback so tests/demos need
  no database.
- `alembic/` + `alembic.ini` with an initial migration creating `notes` /
  `note_chunks`; verified `upgrade head` / `downgrade base` on SQLite.

### Orchestration, API & worker
- `engine.py` — a `KnowledgeBase` engine shared by the API and worker.
- Rounded out endpoints: `POST /notes/index`, `GET /notes/search`
  (keyword/semantic/hybrid), `POST /notes/chat`, `GET /notes/{id}`,
  `GET /notes/{id}/backlinks`, `GET /graph` (nodes+edges), `GET /tags`,
  `GET /stats`, `GET /health`.
- `worker.py` — real tasks (`kb.index_vault`, `kb.reindex`) via
  `shared_core.tasks.create_celery_app`, importable with no broker.

### Tests & data
- Test suite expanded from 16 → 100: embeddings, keyword + semantic search, graph
  export, indexer/frontmatter/tags, chat citations, persistence (SQLite via
  `MockDatabase`), engine end-to-end, worker, every API endpoint (success + error),
  and golden/regression tests pinning embedding output, citation scores, and
  semantic ranking.
- Richer `demo_vault/` (10 interlinked notes with frontmatter, tags, aliases) and a
  full end-to-end `examples/run_demo.py`.

### Docs
- Rewrote `architecture` (with Mermaid), `design-decisions`, `failure-modes`,
  `roadmap`, `security`; added this `EXECUTION_PLAN.md`; updated `AGENTS.md` and the
  README.

---

## Verification (all green)

| Check | Result |
|-------|--------|
| `ruff format` + `ruff check apps/api/src tests examples` | clean |
| `pytest -q` | 100 passed |
| `examples/run_demo.py` | exit 0 |
| `alembic upgrade head` (sqlite) | creates `notes`, `note_chunks` |

---

## Known gaps / out of scope

- `/notes/index` runs synchronously in-process; the worker task exists but the
  endpoint does not yet dispatch to it.
- Path-sandbox hardening for `/notes/index` is documented but not enforced.
- pgvector and real OpenAI/Anthropic paths are wired and unit-covered via the
  offline equivalents, but not exercised against live infrastructure in CI.
