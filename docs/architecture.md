# Architecture — Personal Knowledge Base OS

This document describes the components, data flow, and persistence model of the
Personal Knowledge Base OS API service.

---

## 1. System overview

The service turns a folder of markdown files (a "vault") into a queryable
knowledge base. It is offline-first: it boots and serves with **no database, no
API key, and no network**, and transparently upgrades to PostgreSQL + pgvector +
real LLM/embedding providers when those are configured.

The pipeline has five layers:

1. **Ingestion (`indexer.py`)** — parses markdown via `shared_core.docparse`,
   strips YAML frontmatter, extracts `[[wikilinks]]`, `#hashtags`, and metadata,
   and chunks each note for embedding.
2. **Embedding (`embeddings.py`)** — wraps `shared_core.embeddings`: a
   deterministic offline hash fallback by default, the real OpenAI endpoint when
   `OPENAI_API_KEY` is set.
3. **Retrieval (`search.py`)** — keyword scoring + semantic vector search over
   `shared_core.vectorstore` (in-memory offline, pgvector when keyed).
4. **Graph (`graph.py`)** — bidirectional backlinks adjacency + a `{nodes, edges}`
   export for a visualization UI.
5. **Orchestration + API (`engine.py`, `main.py`)** — the `KnowledgeBase` engine
   ties the layers together; FastAPI exposes them as REST endpoints.

Persistence (`db.py`, `store.py`, `models.py`) and the Celery worker (`worker.py`)
sit alongside, both selecting their backend from the same DB-availability probe.

---

## 2. Component diagram

```mermaid
graph TD
    Client["Client / Dashboard"] --> API["FastAPI<br/>main.py"]
    API --> Engine["KnowledgeBase<br/>engine.py"]

    Engine --> Indexer["NotesIndexer<br/>indexer.py"]
    Engine --> Embedder["EmbeddingGenerator<br/>embeddings.py"]
    Engine --> Search["keyword / semantic search<br/>search.py"]
    Engine --> Graph["BacklinksGraph<br/>graph.py"]
    Engine --> Chat["chat_with_citations<br/>chat.py"]

    Indexer -->|"docparse parse + chunk"| SC1["shared_core.docparse"]
    Embedder -->|"hash fallback / OpenAI"| SC2["shared_core.embeddings"]
    Search -->|"cosine query"| VS["shared_core.vectorstore<br/>(InMemory | PgVector)"]
    Chat -->|"sim / real LLM"| SC3["shared_core.llm"]
    Chat -->|"citation grounding"| SC4["shared_core.evaljudge<br/>CitationJudge"]

    Engine --> Store["NoteStore<br/>store.py"]
    Store -->|"DB probe"| DB["db.py<br/>db_available?"]
    DB -->|reachable| PG[("PostgreSQL")]
    DB -->|offline| MEM["InMemoryNoteStore"]

    Indexer -->|read .md| FS["Markdown Vault"]
    API --> Worker["Celery worker<br/>worker.py"]
```

---

## 3. Indexing sequence

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI (main.py)
    participant KB as KnowledgeBase (engine.py)
    participant Idx as NotesIndexer
    participant Emb as EmbeddingGenerator
    participant VS as VectorStore
    participant G as BacklinksGraph
    participant S as NoteStore

    Client->>API: POST /notes/index {path}
    API->>KB: index_vault(path)
    KB->>Idx: parse_directory(path)
    loop each .md file (recursive)
        Idx->>Idx: strip frontmatter, extract links/tags
        Idx->>Idx: chunk body (semantic)
    end
    Idx-->>KB: [note dicts with chunks]
    KB->>Emb: embed_chunks(chunks)
    KB->>S: replace_all(notes)
    KB->>VS: add chunk vectors
    KB->>G: build_graph(notes)
    KB-->>API: {total_notes, total_chunks, total_links, total_tags}
    API-->>Client: summary + graph {nodes, edges}
```

---

## 4. Chat (RAG) sequence

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant KB as KnowledgeBase
    participant VS as VectorStore
    participant LLM as LLM (sim | real)
    participant J as CitationJudge

    Client->>API: POST /notes/chat {query}
    API->>KB: chat(query)
    KB->>VS: semantic_search(query)
    VS-->>KB: top note chunks
    KB->>LLM: grounded prompt with [n] context
    alt offline / no key
        LLM-->>KB: deterministic stitched answer with [n]
    else real (keyed)
        LLM-->>KB: model answer citing [n]
    end
    KB->>J: evaluate citation grounding
    J-->>KB: passed + score
    KB-->>API: {answer, citations, grounded, citation_score}
    API-->>Client: cited answer
```

---

## 5. Persistence model

Two layers serve different needs:

- **Relational store (`store.py` + `models.py`)** — `notes` and `note_chunks`
  tables hold the canonical note content, links, tags, metadata, and chunk
  embeddings (embeddings as JSON so the schema is SQLite-compatible for the
  offline test fallback). Managed by Alembic (`alembic/`).
- **Vector store (`shared_core.vectorstore`)** — the search index. In-memory and
  recomputable offline; pgvector (`note_vectors` table, `notes` namespace) when a
  database is configured.

The DB-availability probe (`db.py`) does a fast ~0.25s TCP pre-check followed by a
`SELECT 1`. On success notes persist to PostgreSQL and survive restarts (the
engine rebuilds the graph + vectors from the store on startup via
`reindex_from_store`). On failure everything falls back to in-memory.

---

## 6. Module inventory

| Module | Responsibility |
|--------|----------------|
| `main.py` | FastAPI app, endpoints, lifespan DB probe, middleware |
| `engine.py` | `KnowledgeBase` orchestration (index / search / chat / graph) |
| `indexer.py` | Parse, chunk, extract wikilinks / tags / frontmatter |
| `embeddings.py` | Sync facade over `shared_core.embeddings` (offline/real) |
| `search.py` | Keyword scorer + semantic vector retrieval |
| `chat.py` | RAG answer (sim/real LLM) + `CitationJudge` grounding |
| `graph.py` | Backlinks adjacency + `{nodes, edges}` export |
| `store.py` | `InMemoryNoteStore` + `DatabaseNoteStore` |
| `db.py` | DB-availability probe + store selection |
| `models.py` | SQLAlchemy `Note` / `NoteChunk` |
| `worker.py` | Celery tasks (`kb.index_vault`, `kb.reindex`) |
| `config.py` | `AppConfig` (extends `shared_core` `BaseAppConfig`) |
