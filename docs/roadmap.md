# Roadmap — Personal Knowledge Base OS

---

## Milestone 1 — Local ingestion & graph core (done)
- Monorepo API layout under `apps/api/src/`.
- Obsidian `[[wikilink]]` parser and bidirectional backlinks graph.
- Recursive directory ingestion and keyword search.

## Milestone 2 — Retrieval, RAG, and persistence (done)
- Real embeddings via `shared_core.embeddings` (offline hash fallback default,
  OpenAI when keyed) — replaced the old `MockEmbeddingGenerator`.
- Semantic + hybrid search over `shared_core.vectorstore` (in-memory offline,
  pgvector when keyed), with chunk-to-note roll-up.
- Markdown parsing + chunking via `shared_core.docparse`; YAML frontmatter, tag,
  and metadata extraction.
- Chat-with-citations: simulated/real LLM answer scored with
  `shared_core.evaljudge.CitationJudge`.
- Database persistence (`notes` / `note_chunks`) with graceful in-memory fallback
  and Alembic migrations.
- Celery worker tasks (`kb.index_vault`, `kb.reindex`) via
  `shared_core.tasks.create_celery_app`.
- Endpoints: index, keyword/semantic/hybrid search, chat, note + backlinks,
  `{nodes, edges}` graph, tags, stats, health.
- Comprehensive tests (unit, integration, API, worker, golden/regression) and a
  richer demo vault.

## Milestone 3 — Graph UI & live editing (planned)
- `apps/web/` (Next.js) force-directed graph visualization over `/graph`.
- Node-side markdown editor that reads `/notes/{id}` and writes back to disk.
- Dangling-link highlighting using a graph response that flags unresolved targets.
- Live events / WebSocket stream so the dashboard updates as the vault changes.

## Milestone 4 — Sync, watching, and study tools (future)
- Filesystem watcher (`watchdog`) to re-index on note add/edit/delete.
- Incremental indexing (content-hash diffing) instead of full re-index.
- Multi-vault workspaces with per-vault namespaces in the vector store.
- LLM-generated spaced-repetition flashcards from notes.
- Saved searches and tag-scoped semantic queries.
