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
- **How**: `shared_core.embeddings.get_embedding_provider(offline=True)` (hash
  fallback), `shared_core.vectorstore.get_vector_store(offline=True)` (in-memory),
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

## 3. Reuse `shared_core` instead of bespoke logic

- **Decision**: Use `shared_core.docparse` for parsing/chunking,
  `shared_core.embeddings` for vectors, `shared_core.vectorstore` for retrieval,
  and `shared_core.evaljudge.CitationJudge` for grounding — rather than
  hand-rolling each.
- **Rationale**: These are the convergence points across the portfolio; reusing
  them keeps behavior consistent and battle-tested. The previous
  `MockEmbeddingGenerator` was replaced with the shared provider, and golden tests
  pin the output so a future swap can't silently drift the rankings.

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
