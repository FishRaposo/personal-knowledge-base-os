"""FastAPI application for Personal Knowledge Base OS.

Offline-first: boots and serves with NO database (in-memory note + vector stores),
NO API key (deterministic offline embeddings + simulated cited chat), and NO
network. When a database is reachable the ``db_available`` probe upgrades the note
store to PostgreSQL and vectors to pgvector. Exposes everything a knowledge-base
dashboard needs: index, keyword/semantic/hybrid search, RAG chat with citations,
note + backlinks browsing, a graph (nodes+edges) for visualization, and tags.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional, cast

from fastapi import FastAPI, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import db as db_module
from .config import AppConfig
from .engine import KnowledgeBase
from .graph import BacklinksGraph
from .indexer import NotesIndexer
from .internal.vendor_core.errors import (
    BaseApplicationError,
    NotFoundError,
    ValidationError,
    application_error_handler,
)
from .internal.vendor_core.health import check_health
from .internal.vendor_core.logging import RequestLoggingMiddleware, setup_logging
from .internal.vendor_core.redis import RedisManager
from .internal.vendor_core.vectorstore import get_vector_store

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

app.add_exception_handler(BaseApplicationError, cast(Any, application_error_handler))
app.add_middleware(RequestLoggingMiddleware)


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class IndexRequest(BaseModel):
    """Index a vault directory. Defaults to the configured demo vault."""

    path: Optional[str] = Field(default=None, description="Vault directory path.")
    vault_id: str = "default"
    incremental: bool = False


class ChatRequest(BaseModel):
    query: str = Field(description="Question to answer over the notes.")
    limit: int = Field(default=3, ge=1, le=10)
    vault_id: str = "default"


class VaultRequest(BaseModel):
    vault_id: str
    path: str
    name: Optional[str] = None


class NoteUpdateRequest(BaseModel):
    content: str
    vault_id: str = "default"


class SavedSearchRequest(BaseModel):
    name: str
    query: str
    mode: str = Field(default="keyword", pattern="^(keyword|semantic|hybrid)$")
    tags: List[str] = Field(default_factory=list)
    vault_id: str = "default"


class FlashcardGenerateRequest(BaseModel):
    vault_id: str = "default"
    note_id: Optional[str] = None
    enrich: bool = False


class FlashcardReviewRequest(BaseModel):
    vault_id: str = "default"
    rating: int = Field(ge=0, le=5)


def _vault_path(vault_id: str, requested: Optional[str] = None) -> str:
    """Resolve an API indexing path against an explicitly configured vault."""
    metadata = kb.vault_metadata(vault_id)
    root = metadata.get("path")
    if requested is None:
        if not root:
            raise ValidationError(f"Vault '{vault_id}' has no configured path.")
        return str(root)
    requested_path = Path(requested)
    if root and requested_path.resolve(strict=False) != Path(root).resolve(
        strict=False
    ):
        raise ValidationError("Index path is outside the configured vault root.")
    # Preserve the unresolved spelling for the engine's symlink-component guard.
    return str(requested_path)


@app.get("/vaults")
def list_vaults():
    return {"vaults": kb.list_vaults(), "selected": kb.selected_vault_id}


@app.post("/vaults")
def create_vault(payload: VaultRequest):
    try:
        return kb.register_vault(payload.vault_id, payload.path, name=payload.name)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


@app.post("/vaults/{vault_id}/select")
def select_vault(vault_id: str):
    try:
        return kb.select_vault(vault_id)
    except KeyError as exc:
        raise NotFoundError(f"Vault '{vault_id}' not found") from exc


# --------------------------------------------------------------------------- #
# Indexing
# --------------------------------------------------------------------------- #
@app.post("/notes/index")
def index_notes(payload: IndexRequest):
    """Ingest all markdown files under a vault path (parse, chunk, embed, graph)."""
    path = _vault_path(payload.vault_id, payload.path)
    try:
        summary = kb.index_vault(
            path, vault_id=payload.vault_id, incremental=payload.incremental
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValidationError(str(exc)) from exc
    if summary["total_notes"] == 0:
        raise ValidationError(f"No markdown notes found under '{path}'.")
    return {**summary, "graph": kb.get_graph(vault_id=payload.vault_id)}


@app.get("/notes/index")
def index_notes_get(
    path: Optional[str] = None,
    vault_id: str = "default",
    incremental: bool = False,
):
    """GET convenience wrapper around POST /notes/index (dashboard-friendly)."""
    resolved = _vault_path(vault_id, path)
    try:
        summary = kb.index_vault(resolved, vault_id=vault_id, incremental=incremental)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValidationError(str(exc)) from exc
    if summary["total_notes"] == 0:
        raise ValidationError(f"No markdown notes found under '{resolved}'.")
    return {**summary, "graph": kb.get_graph(vault_id=vault_id)}


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #
@app.get("/notes/search")
def search_notes(
    q: str = Query(description="Search query"),
    limit: int = Query(default=5, ge=1, le=50),
    mode: str = Query(default="keyword", pattern="^(keyword|semantic|hybrid)$"),
    vault_id: str = "default",
    tags: Optional[str] = None,
):
    """Search indexed notes by keyword, semantic similarity, or hybrid."""
    tag_list = [tag.strip() for tag in (tags or "").split(",") if tag.strip()]
    results = kb.search(q, limit, mode=mode, vault_id=vault_id, tags=tag_list)
    return {"query": q, "mode": mode, "results": results, "total": len(results)}


# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #
@app.post("/notes/chat")
def chat_with_notes(payload: ChatRequest):
    """Answer a question over the notes with grounded inline citations."""
    return kb.chat(payload.query, limit=payload.limit, vault_id=payload.vault_id)


# --------------------------------------------------------------------------- #
# Browsing
# --------------------------------------------------------------------------- #
@app.patch("/notes/{note_id}")
def update_note(note_id: str, payload: NoteUpdateRequest):
    try:
        note = kb.update_note(note_id, payload.content, vault_id=payload.vault_id)
    except KeyError as exc:
        raise NotFoundError(f"Note '{note_id}' not found") from exc
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValidationError(str(exc)) from exc
    return {
        **note,
        "backlinks": kb.get_backlinks(note_id, vault_id=payload.vault_id),
    }


@app.get("/notes/{note_id}")
def get_note(note_id: str, vault_id: str = "default"):
    """Return a single note's content, links, tags, and metadata."""
    note = kb.get_note(note_id, vault_id=vault_id)
    if note is None:
        raise NotFoundError(f"Note '{note_id}' not found")
    return {**note, "backlinks": kb.get_backlinks(note_id, vault_id=vault_id)}


@app.get("/notes/{note_id}/backlinks")
def note_backlinks(note_id: str, vault_id: str = "default"):
    """Return all notes that link to the specified note."""
    return {
        "note_id": note_id,
        "backlinks": kb.get_backlinks(note_id, vault_id=vault_id),
    }


# --------------------------------------------------------------------------- #
# Graph & tags (dashboard data)
# --------------------------------------------------------------------------- #
@app.get("/graph")
def get_graph(vault_id: str = "default"):
    """Return the note graph as ``{nodes, edges}`` for a visualization UI."""
    return kb.get_graph(vault_id=vault_id)


@app.get("/tags")
def get_tags(vault_id: str = "default"):
    """Return tag -> note-count rollup across the vault."""
    return {"tags": kb.list_tags(vault_id=vault_id)}


@app.get("/stats")
def get_stats(vault_id: str = "default"):
    """Return index statistics (note/chunk/tag counts)."""
    return kb.stats(vault_id=vault_id)


# --------------------------------------------------------------------------- #
# Saved searches, flashcards, watcher status, and live events
# --------------------------------------------------------------------------- #
@app.get("/saved-searches")
def list_saved_searches(vault_id: str = "default"):
    return {"saved_searches": kb.list_saved_searches(vault_id=vault_id)}


@app.post("/saved-searches")
def create_saved_search(payload: SavedSearchRequest):
    try:
        return kb.save_search(
            name=payload.name,
            query=payload.query,
            mode=payload.mode,
            tags=payload.tags,
            vault_id=payload.vault_id,
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


@app.delete("/saved-searches/{search_id}")
def delete_saved_search(search_id: str, vault_id: str = "default"):
    if not kb.delete_saved_search(search_id, vault_id=vault_id):
        raise NotFoundError(f"Saved search '{search_id}' not found")
    return {"deleted": True, "id": search_id}


@app.post("/flashcards/generate")
def generate_flashcards(payload: FlashcardGenerateRequest):
    cards = kb.generate_flashcards(
        vault_id=payload.vault_id,
        note_id=payload.note_id,
        enrich=payload.enrich,
    )
    return {
        "cards": cards,
        "total": len(cards),
        "fallback": any(not card.get("enriched", False) for card in cards),
    }


@app.get("/flashcards")
def list_flashcards(vault_id: str = "default"):
    cards = kb.flashcards.list(vault_id=vault_id)
    return {"cards": cards, "total": len(cards)}


@app.post("/flashcards/{card_id}/review")
def review_flashcard(card_id: str, payload: FlashcardReviewRequest):
    try:
        return kb.flashcards.review(
            card_id, rating=payload.rating, vault_id=payload.vault_id
        )
    except KeyError as exc:
        raise NotFoundError(f"Flashcard '{card_id}' not found") from exc
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


@app.get("/watchers/{vault_id}")
def watcher_status(vault_id: str):
    return kb.watcher_status(vault_id)


@app.post("/watchers/{vault_id}/start")
def start_watcher(vault_id: str):
    try:
        return kb.start_watcher(vault_id)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


@app.post("/watchers/{vault_id}/stop")
def stop_watcher(vault_id: str):
    return kb.stop_watcher(vault_id)


@app.get("/events/replay")
def replay_events(vault_id: str = "default", last_event_id: Optional[str] = None):
    events = kb.events.replay(vault_id=vault_id, after_id=last_event_id)
    return {
        "events": events,
        "last_event_id": events[-1]["id"] if events else last_event_id,
    }


@app.get("/events")
def stream_events(
    vault_id: str = "default",
    last_event_id: Optional[str] = None,
    last_event_header: Optional[str] = Header(default=None, alias="Last-Event-ID"),
):
    cursor = last_event_id or last_event_header
    return StreamingResponse(
        kb.events.stream(vault_id=vault_id, after_id=cursor),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
