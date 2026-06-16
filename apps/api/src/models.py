"""SQLAlchemy models backing the default PostgreSQL persistence path.

Two tables: ``notes`` (one row per markdown note, with links/tags/metadata as
JSON) and ``note_chunks`` (the embeddable slices, embeddings stored as JSON so
the schema stays SQLite-compatible for the offline in-memory fallback). The
*vector search* path lives in ``shared_core.vectorstore`` (in-memory by default,
pgvector when a database is configured), so this relational store does not need a
native vector column to function.
"""

from shared_core.database import Base, TimestampMixin, UUIDMixin
from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text


class Note(Base, UUIDMixin, TimestampMixin):
    """An ingested markdown note with its links, tags, and metadata."""

    __tablename__ = "notes"

    note_id = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    source = Column(String(1000), nullable=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    word_count = Column(Integer, default=0)
    links = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    note_metadata = Column(JSON, nullable=True)


class NoteChunk(Base, UUIDMixin, TimestampMixin):
    """An embeddable slice of a note (content + JSON embedding vector)."""

    __tablename__ = "note_chunks"

    chunk_id = Column(String(512), nullable=False, unique=True, index=True)
    note_id = Column(
        String(255), ForeignKey("notes.note_id"), nullable=False, index=True
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)
    embedding = Column(JSON, nullable=True)
