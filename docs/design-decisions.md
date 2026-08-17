# Design Decisions — Personal Knowledge Base OS

The reasoning behind the major technical choices in this service.

---

## 1. Offline-first, real-when-keyed

- **Decision**: Every external dependency (database, embeddings, LLM, Redis) has a
  deterministic offline default and a real implementation that activates only when
  configured.
- **Rationale**: The project must run, test, and demo with no API keys, no
  database, and no network. Deterministic defaults also make the test suite
  reproducible — the offline hash embeddings and simulated chat answer return the
  same output every run.
- **How**: internal `vendor_core.embeddings.get_embedding_provider(offline=True)` (hash
  fallback), internal `vendor_core.vectorstore.get_vector_store(offline=True)` (in-memory),
  a simulated chat answer mirroring `llm-cost-latency-monitor`'s SDK, and a DB
  probe with in-memory fallback.

---

## 2. Two stores: relational + vector

- **Decision**: Keep the canonical note content in a relational store and the
  search index in a separate vector store, rather than forcing one table to do
  both.
- **Rationale**: They have different shapes and lifecycles. Notes/links/tags are
  relational and queried by id; vectors are queried by similarity. Splitting them
  lets the relational schema stay SQLite-compatible (embeddings as JSON) so tests
  run on in-memory SQLite, while production search uses pgvector.
- **Trade-off**: The vector index must be rebuilt from the store on startup
  (`reindex_from_store`). This is cheap for personal-scale vaults and avoids a
  pgvector dependency in the relational path.

---

## 3. Internal vendor namespace, not sibling restoration

- **Decision**: Use the pinned internal `apps.api.src.internal.vendor_core` closure for parsing/chunking,
  `vendor_core.embeddings` for vectors, `vendor_core.vectorstore` for retrieval,
  and `vendor_core.evaljudge.CitationJudge` for grounding — rather than
  hand-rolling each.
- **Rationale**: The vendor closure preserves the proven contracts without an
  install-time sibling checkout, Git URL dependency, or external `shared_core`
  import. It is pinned to `operator-shared-core` v1.3.0 at
  `dbf276a7708da65b55e1f10b35af634b300d1f07`; provenance and namespace-only
  patches are in `THIRD_PARTY_NOTICES.md`.
- **Policy**: database, Redis, Celery, providers, watchdog, OCR, and heavy
  parser/model capabilities are optional extras. The default `dev` path must
  remain deterministic and offline-capable.

---

## 4. Wikilink graph with slug resolution

- **Decision**: Parse Obsidian-style `[[wikilinks]]` (not standard markdown links)
  and resolve link targets to note ids via slugs.
- **Rationale**: Wikilinks are the connection format of Obsidian / Logseq / Roam,
  so users can point the service at an existing vault. Slug resolution means
  `[[Note Architecture]]`, `[[note_architecture]]`, and `[[note-architecture]]` all
  resolve to the same node, which is how authors actually write links.
- **Trade-off**: Standard `[text](url)` markdown links are ignored. Aliased links
  (`[[target|display]]`) keep the target.

---

## 5. Chat must cite, and the citation is scored

- **Decision**: Every chat answer carries inline `[n]` markers, and the grounding
  is *scored* with `CitationJudge`, not merely formatted.
- **Rationale**: A knowledge-base assistant that paraphrases without attribution is
  untrustworthy. Scoring the citation presence turns "the answer looks cited" into
  an assertion we can test (`grounded`, `citation_score`) and that survives the
  swap from simulated to real LLM.
- **Behavior**: With no relevant notes, chat refuses (`grounded=False`) rather than
  hallucinating.

---

## 6. A `KnowledgeBase` engine shared by API and worker

- **Decision**: Put orchestration in `engine.py` rather than the FastAPI handlers.
- **Rationale**: The Celery worker and the API need identical index/search/chat
  logic. A single engine class keeps them in lockstep and makes the core logic
  unit-testable without an HTTP client or a broker.

---

## 7. Monorepo layout (`apps/api/src/`)

- **Decision**: Keep the backend under `apps/api/` with the Python package root at
  `apps/api/src` (loose modules imported via the `apps.api.src` package), leaving
  room for a future `apps/web/`.
- **Rationale**: A knowledge base wants a rich graph UI. Isolating the Python
  service from a future Node/React frontend keeps environments modular. The API
  already exposes everything a dashboard needs (search, graph, chat, tags, stats)
  so the frontend is purely additive.

---

## 8. Additive vault namespaces and local state

- **Decision**: Add `vault_id` to new and existing operations while preserving
  `vault_id="default"` as the legacy namespace.
- **Rationale**: A personal workspace can keep independent vaults without
  changing existing API calls or mixing retrieval, graph, event, and review data.
- **Boundary**: This is service-level local isolation, not authentication or
  hosted tenancy. Persistent adapters may use composite vault predicates; the
  in-memory path applies the same scope rules.

---

## 9. Polling watcher with SSE, not mandatory infrastructure

- **Decision**: Use an explicitly started standard-library polling watcher and
  bounded replayable SSE events. Watchdog can accelerate a deployment only when
  installed.
- **Rationale**: Polling works in the offline demo and avoids import-time side
  effects. SSE supports a simple dashboard live-update channel; polling replay is
  retained for clients that cannot hold an event stream.
- **Boundary**: event IDs and replay are local runtime metadata, not a durable
  distributed message bus or hosted collaboration promise.

---

## 10. Deterministic cards before optional enrichment

- **Decision**: Generate stable, source-cited flashcards from headings and
  paragraphs, then keep review scheduling locally. An optional provider can
  enrich content but cannot be required for generation.
- **Rationale**: Stable IDs, deterministic evidence, and review behavior are
  more useful for an offline-first product than a provider-only card generator.
