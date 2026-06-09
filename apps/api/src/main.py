from fastapi import FastAPI, Query
from shared_core.database import DatabaseManager
from shared_core.errors import BaseApplicationError, application_error_handler
from shared_core.health import check_health
from shared_core.logging import setup_logging
from shared_core.redis import RedisManager

from .chat import chat_with_citations
from .config import AppConfig
from .embeddings import MockEmbeddingGenerator
from .graph import BacklinksGraph
from .indexer import NotesIndexer
from .search import keyword_search

config = AppConfig()
setup_logging(level=config.LOG_LEVEL, service_name=config.APP_NAME)

app = FastAPI(title=config.APP_NAME, version="0.1.0")
db_manager = DatabaseManager(config.DATABASE_URL)
redis_manager = RedisManager(config.REDIS_URL)

app.add_exception_handler(BaseApplicationError, application_error_handler)

indexer = NotesIndexer()
graph = BacklinksGraph()
embedder = MockEmbeddingGenerator()
_search_index: list[dict] = []


@app.get("/notes/index")
def index_notes(path: str):
    global _search_index
    notes = indexer.parse_directory(path)
    graph.build_graph(notes)
    _search_index = notes
    graph_data = {k: list(v) for k, v in graph.adj_list.items()}
    return {"total_notes": len(notes), "graph": graph_data, "notes": notes}


@app.get("/notes/search")
def search_notes(q: str = Query(description="Search query"), limit: int = 5):
    results = keyword_search(_search_index, q, limit)
    return {"query": q, "results": results, "total": len(results)}


@app.post("/notes/chat")
def chat_with_notes(q: str = Query(description="Chat query")):
    retrieved = keyword_search(_search_index, q, limit=3)
    result = chat_with_citations(q, retrieved)
    return result


@app.get("/notes/{note_id}/backlinks")
def note_backlinks(note_id: str):
    backlinks = graph.get_backlinks(note_id)
    return {"note_id": note_id, "backlinks": backlinks}


@app.get("/health")
def health_check():
    return check_health(db_manager, redis_manager, config.APP_NAME)
