"""FastAPI application for Personal Knowledge Base OS.

Offline-first: boots and serves with NO database (in-memory note + vector stores),
NO API key (deterministic offline embeddings + simulated cited chat), and NO
network. When a database is reachable the ``db_available`` probe upgrades the note
store to PostgreSQL and vectors to pgvector. Exposes everything a knowledge-base
dashboard needs: index, keyword/semantic/hybrid search, RAG chat with citations,
note + backlinks browsing, a graph (nodes+edges) for visualization, and tags.
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from shared_core.errors import (
    BaseApplicationError,
    NotFoundError,
    ValidationError,
    application_error_handler,
)
from shared_core.health import check_health
from shared_core.logging import RequestLoggingMiddleware, setup_logging
from shared_core.redis import RedisManager
from shared_core.vectorstore import get_vector_store

from . import db as db_module
from .config import AppConfig
from .engine import KnowledgeBase
from .graph import BacklinksGraph
from .indexer import NotesIndexer

config = AppConfig()
setup_logging(level=config.LOG_LEVEL, service_name=config.APP_NAME)

# Offline-first defaults; the startup probe upgrades the stores when a database is
# reachable. Tests patch these module globals directly.
kb = KnowledgeBase(config=config)

# Exposed for backwards-compatible tests that patch these names directly.
indexer: NotesIndexer = kb.indexer
graph: BacklinksGraph = kb.graph

db_manager = db_module.db_manager
redis_manager = RedisManager(config.REDIS_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Probe the database on startup and select persistence backends."""
    db_module.check_db()
    if db_module.db_available:
        kb.note_store = db_module.build_store()
        vector_store = get_vector_store(
            offline=False,
            db_manager=db_module.db_manager,
            dimensions=kb.embedder.dimensions,
            table="note_vectors",
            namespace="notes",
        )
        if hasattr(vector_store, "setup"):
            try:
                vector_store.setup()
                kb.vector_store = vector_store
            except Exception:  # noqa: BLE001 - non-fatal; keep in-memory vectors
                pass
        kb.reindex_from_store()
    yield


app = FastAPI(
    title=config.APP_NAME,
    version="1.0.0",
    description=(
        "Local-first knowledge base: ingest a markdown vault, parse wikilinks into "
        "a bidirectional backlinks graph, search by keyword or semantics, and chat "
        "over your notes with grounded citations."
    ),
    lifespan=lifespan,
)

app.add_exception_handler(BaseApplicationError, application_error_handler)
app.add_middleware(RequestLoggingMiddleware)


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class IndexRequest(BaseModel):
    """Index a vault directory. Defaults to the configured demo vault."""

    path: Optional[str] = Field(default=None, description="Vault directory path.")


class ChatRequest(BaseModel):
    query: str = Field(description="Question to answer over the notes.")
    limit: int = Field(default=3, ge=1, le=10)


# --------------------------------------------------------------------------- #
# Indexing
# --------------------------------------------------------------------------- #
@app.post("/notes/index")
def index_notes(payload: IndexRequest):
    """Ingest all markdown files under a vault path (parse, chunk, embed, graph)."""
    path = payload.path or config.DEFAULT_VAULT_PATH
    summary = kb.index_vault(path)
    if summary["total_notes"] == 0:
        raise ValidationError(f"No markdown notes found under '{path}'.")
    return {**summary, "graph": kb.get_graph()}


@app.get("/notes/index")
def index_notes_get(path: Optional[str] = None):
    """GET convenience wrapper around POST /notes/index (dashboard-friendly)."""
    summary = kb.index_vault(path or config.DEFAULT_VAULT_PATH)
    return {**summary, "graph": kb.get_graph()}


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #
@app.get("/notes/search")
def search_notes(
    q: str = Query(description="Search query"),
    limit: int = Query(default=5, ge=1, le=50),
    mode: str = Query(default="keyword", pattern="^(keyword|semantic|hybrid)$"),
):
    """Search indexed notes by keyword, semantic similarity, or hybrid."""
    results = kb.search(q, limit, mode=mode)
    return {"query": q, "mode": mode, "results": results, "total": len(results)}


# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #
@app.post("/notes/chat")
def chat_with_notes(payload: ChatRequest):
    """Answer a question over the notes with grounded inline citations."""
    return kb.chat(payload.query, limit=payload.limit)


# --------------------------------------------------------------------------- #
# Browsing
# --------------------------------------------------------------------------- #
@app.get("/notes/{note_id}")
def get_note(note_id: str):
    """Return a single note's content, links, tags, and metadata."""
    note = kb.get_note(note_id)
    if note is None:
        raise NotFoundError(f"Note '{note_id}' not found")
    return {**note, "backlinks": kb.get_backlinks(note_id)}


@app.get("/notes/{note_id}/backlinks")
def note_backlinks(note_id: str):
    """Return all notes that link to the specified note."""
    return {"note_id": note_id, "backlinks": kb.get_backlinks(note_id)}


# --------------------------------------------------------------------------- #
# Graph & tags (dashboard data)
# --------------------------------------------------------------------------- #
@app.get("/graph")
def get_graph():
    """Return the note graph as ``{nodes, edges}`` for a visualization UI."""
    return kb.get_graph()


@app.get("/tags")
def get_tags():
    """Return tag -> note-count rollup across the vault."""
    return {"tags": kb.list_tags()}


@app.get("/stats")
def get_stats():
    """Return index statistics (note/chunk/tag counts)."""
    return kb.stats()


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.get("/health")
def health_check():
    """Service health, probing database and Redis connectivity."""
    return check_health(db_manager, redis_manager, config.APP_NAME)


def main():
    """Run the development server."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
