# Roadmap — Personal Knowledge Base OS

---

## Milestone 1 — Local ingestion & graph core (done)
- Monorepo API layout under `apps/api/src/`.
- Obsidian `[[wikilink]]` parser and bidirectional backlinks graph.
- Recursive directory ingestion and keyword search.

## Milestone 2 — Retrieval, RAG, and persistence (done)
- Real embeddings via internal `vendor_core.embeddings` (offline hash fallback default,
  OpenAI when keyed) — replaced the old `MockEmbeddingGenerator`.
- Semantic + hybrid search over internal `vendor_core.vectorstore` (in-memory offline,
  pgvector when keyed), with chunk-to-note roll-up.
- Markdown parsing + chunking via internal `vendor_core.docparse`; YAML frontmatter, tag,
  and metadata extraction.
- Chat-with-citations: simulated/real LLM answer scored with
  internal `vendor_core.evaljudge.CitationJudge`.
- Database persistence (`notes` / `note_chunks`) with graceful in-memory fallback
  and Alembic migrations.
- Celery worker tasks (`kb.index_vault`, `kb.reindex`) via
  internal `vendor_core.tasks.create_celery_app`.
- Endpoints: index, keyword/semantic/hybrid search, chat, note + backlinks,
  `{nodes, edges}` graph, tags, stats, health.
- Comprehensive tests (unit, integration, API, worker, golden/regression) and a
  richer demo vault.

## Milestone 3 — Graph UI & live editing (delivered)
- Next.js dashboard graph, note view/edit actions, and demo fixtures.
- Additive dangling-link metadata while retaining the legacy `{nodes, edges}` graph shape.
- Safe configured-root editing with symlink/path-escape refusal and deterministic events.
- Replayable SSE (`/events`) and a polling fallback; watcher/index/editor event vocabulary is stable.

## Milestone 4 — Sync, watching, and study tools (delivered locally)
- Explicit stdlib polling watcher with optional watchdog acceleration; no watcher starts at API boot.
- Content-hash incremental indexing for added, changed, and deleted Markdown notes; full indexing remains the compatibility default.
- Multi-vault namespaces with `vault_id="default"` legacy compatibility and scoped retrieval, graph, tags, chat, saved searches, cards, and events.
- Deterministic source-cited flashcards and local review scheduling; provider enrichment is optional and falls back locally.
- Saved searches and tag-scoped keyword/semantic/hybrid retrieval.

## Deliberately deferred

Authentication, hosted/team collaboration, cloud storage, mandatory PostgreSQL/Redis/Celery, hosted scheduling, provider-required workflows, and heavy parser/model installations are out of scope. PostgreSQL/pgvector, Redis, Celery, OpenAI/Anthropic, watchdog, OCR, and document/model integrations remain opt-in extras.
