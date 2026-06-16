"""Database availability probe and note-store selection.

Offline-first with graceful fallback: on startup we do a fast TCP pre-check (so an
unreachable database costs ~0.25s, not the multi-second driver timeout) and then a
``SELECT 1``. If the database is reachable, notes/chunks persist to PostgreSQL via
``DatabaseNoteStore`` and survive restarts; otherwise the service transparently
uses ``InMemoryNoteStore`` so tests and the demo run with NO database.
"""

import socket
from typing import Optional
from urllib.parse import urlsplit

from loguru import logger
from shared_core.database import DatabaseManager
from sqlalchemy import text

from .config import AppConfig
from .store import DatabaseNoteStore, InMemoryNoteStore, NoteStore

config = AppConfig()

db_manager = DatabaseManager(
    config.DATABASE_URL,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
    pool_timeout=config.DB_POOL_TIMEOUT,
)

db_available: bool = False

# Short socket timeout keeps the offline-first fallback fast (the "2s connect
# probe -> in-memory" requirement; we use a tighter 0.25s TCP pre-check).
_SOCKET_TIMEOUT_SECONDS = 0.25


def _db_reachable(url: str) -> bool:
    """Fast TCP pre-check: can we open a socket to the database host:port?"""
    parts = urlsplit(url)
    if parts.scheme.startswith("sqlite"):
        return True
    host = parts.hostname or "localhost"
    port = parts.port or 5432
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return False
    family, socktype, proto, _canon, sockaddr = infos[0]
    sock = socket.socket(family, socktype, proto)
    sock.settimeout(_SOCKET_TIMEOUT_SECONDS)
    try:
        sock.connect(sockaddr)
        return True
    except OSError:
        return False
    finally:
        sock.close()


def check_db() -> bool:
    """Probe database connectivity and cache the result in ``db_available``."""
    global db_available
    if not _db_reachable(config.DATABASE_URL):
        db_available = False
        logger.info("Database host unreachable — using in-memory note store (offline).")
        return db_available
    try:
        with db_manager.SessionLocal() as session:
            session.execute(text("SELECT 1"))
        db_manager.create_tables()
        db_available = True
        logger.info("Database connected — notes will persist to PostgreSQL.")
    except Exception as exc:  # noqa: BLE001 - offline-first fallback
        db_available = False
        logger.warning(
            "Database unavailable — falling back to in-memory note store: {}", exc
        )
    return db_available


def build_store(in_memory_fallback: Optional[InMemoryNoteStore] = None) -> NoteStore:
    """Return the active note store based on the last probe result."""
    if db_available:
        return DatabaseNoteStore(db_manager.get_session)
    return in_memory_fallback or InMemoryNoteStore()
