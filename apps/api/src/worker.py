"""Celery worker with real knowledge-base tasks.

Built on ``shared_core.tasks.create_celery_app``. The module imports with NO
broker running (Celery only connects when a worker starts or ``.delay()`` is
called), so the API and tests import it freely. The pure logic lives in
``_index_vault`` / ``_reindex`` so it is unit-testable without invoking Celery.
Each task builds a fresh ``KnowledgeBase`` bound to the active (DB or in-memory)
store via the ``db_available`` probe.
"""

from typing import Any, Dict

from shared_core.tasks import create_celery_app
from shared_core.vectorstore import get_vector_store

from . import db as db_module
from .config import AppConfig
from .engine import KnowledgeBase

config = AppConfig()
celery_app = create_celery_app(
    config.APP_NAME,
    broker_url=config.CELERY_BROKER_URL,
    backend_url=config.CELERY_RESULT_BACKEND,
)


def _build_kb() -> KnowledgeBase:
    """Construct a KnowledgeBase bound to the active (DB or in-memory) store."""
    db_module.check_db()
    note_store = db_module.build_store()
    kb = KnowledgeBase(config=config, note_store=note_store)
    if db_module.db_available:
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
    return kb


def _index_vault(path: str) -> Dict[str, Any]:
    """Pure vault-indexing (no Celery dependency)."""
    kb = _build_kb()
    return kb.index_vault(path)


def _reindex() -> Dict[str, Any]:
    """Rebuild the graph + vector store from persisted notes."""
    kb = _build_kb()
    kb.reindex_from_store()
    return kb.stats()


@celery_app.task(name="kb.index_vault")
def index_vault_task(path: str) -> Dict[str, Any]:
    """Celery task: index every markdown note under ``path``."""
    return _index_vault(path)


@celery_app.task(name="kb.reindex")
def reindex_task() -> Dict[str, Any]:
    """Celery task: rebuild the graph + vector store from persisted notes."""
    return _reindex()
