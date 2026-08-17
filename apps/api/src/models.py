"""SQLite-compatible persistence models for notes and local-first features."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from .internal.vendor_core.database import Base, TimestampMixin, UUIDMixin


class Vault(Base, UUIDMixin, TimestampMixin):
    """A named local vault namespace."""

    __tablename__ = "vaults"

    vault_id = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(500), nullable=False)
    root_path = Column(String(2000), nullable=True)
    vault_metadata = Column(JSON, nullable=True)


class Note(Base, UUIDMixin, TimestampMixin):
    """An ingested markdown note with its links, tags, and metadata."""

    __tablename__ = "notes"

    __table_args__ = (
        UniqueConstraint("vault_id", "note_id", name="uq_notes_vault_note"),
        Index("ix_notes_vault_note", "vault_id", "note_id"),
    )

    vault_id = Column(
        String(255),
        ForeignKey("vaults.vault_id"),
        nullable=False,
        default="default",
        server_default="default",
        index=True,
    )
    note_id = Column(String(255), nullable=False, index=True)
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

    __table_args__ = (
        ForeignKeyConstraint(
            ["vault_id", "note_id"],
            ["notes.vault_id", "notes.note_id"],
            name="fk_note_chunks_vault_note",
            ondelete="CASCADE",
        ),
        UniqueConstraint("vault_id", "chunk_id", name="uq_chunks_vault_chunk"),
        Index("ix_chunks_vault_note", "vault_id", "note_id"),
    )

    vault_id = Column(
        String(255),
        ForeignKey("vaults.vault_id"),
        nullable=False,
        default="default",
        server_default="default",
        index=True,
    )
    chunk_id = Column(String(512), nullable=False, index=True)
    note_id = Column(String(255), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)
    embedding = Column(JSON, nullable=True)


class FileSnapshot(Base, UUIDMixin, TimestampMixin):
    """Last indexed filesystem state for one vault-relative note path."""

    __tablename__ = "file_snapshots"
    __table_args__ = (
        UniqueConstraint("vault_id", "relative_path", name="uq_snapshot_vault_path"),
        Index("ix_snapshot_vault_hash", "vault_id", "content_hash"),
    )

    vault_id = Column(String(255), ForeignKey("vaults.vault_id"), nullable=False)
    relative_path = Column(String(2000), nullable=False)
    content_hash = Column(String(64), nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    modified_ns = Column(BigInteger, nullable=True)
    snapshot_metadata = Column(JSON, nullable=True)


class SavedSearch(Base, UUIDMixin, TimestampMixin):
    """A deterministic vault-scoped search definition."""

    __tablename__ = "saved_searches"
    __table_args__ = (
        UniqueConstraint(
            "vault_id", "saved_search_id", name="uq_saved_search_vault_id"
        ),
        UniqueConstraint("vault_id", "name", name="uq_saved_search_vault_name"),
    )

    saved_search_id = Column(String(255), nullable=False)
    vault_id = Column(String(255), ForeignKey("vaults.vault_id"), nullable=False)
    name = Column(String(500), nullable=False)
    query = Column(Text, nullable=False, default="")
    tags = Column(JSON, nullable=True)
    search_mode = Column(String(32), nullable=False, default="hybrid")
    search_metadata = Column(JSON, nullable=True)


class Flashcard(Base, UUIDMixin, TimestampMixin):
    """A stable, source-cited flashcard generated from a local note."""

    __tablename__ = "flashcards"
    __table_args__ = (
        ForeignKeyConstraint(
            ["vault_id", "note_id"],
            ["notes.vault_id", "notes.note_id"],
            name="fk_flashcards_vault_note",
            ondelete="CASCADE",
        ),
        UniqueConstraint("vault_id", "flashcard_id", name="uq_flashcard_vault_id"),
    )

    flashcard_id = Column(String(255), nullable=False)
    vault_id = Column(String(255), ForeignKey("vaults.vault_id"), nullable=False)
    note_id = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source_citations = Column(JSON, nullable=False, default=list)
    card_metadata = Column(JSON, nullable=True)


class FlashcardReviewState(Base, UUIDMixin, TimestampMixin):
    """Local spaced-repetition state for one vault-scoped flashcard."""

    __tablename__ = "flashcard_review_state"
    __table_args__ = (
        ForeignKeyConstraint(
            ["vault_id", "flashcard_id"],
            ["flashcards.vault_id", "flashcards.flashcard_id"],
            name="fk_review_vault_card",
            ondelete="CASCADE",
        ),
        UniqueConstraint("vault_id", "flashcard_id", name="uq_review_vault_card"),
    )

    flashcard_id = Column(String(255), nullable=False)
    vault_id = Column(String(255), ForeignKey("vaults.vault_id"), nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=False)
    interval_days = Column(Integer, nullable=False, default=0)
    ease_factor = Column(Float, nullable=False, default=2.5)
    repetitions = Column(Integer, nullable=False, default=0)
    last_rating = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


class WatcherState(Base, UUIDMixin, TimestampMixin):
    """Persisted watcher cursor without implying an automatically running process."""

    __tablename__ = "watcher_state"
    __table_args__ = (UniqueConstraint("vault_id", name="uq_watcher_vault"),)

    vault_id = Column(String(255), ForeignKey("vaults.vault_id"), nullable=False)
    running = Column(Boolean, nullable=False, default=False)
    last_event_id = Column(String(255), nullable=True)
    scan_hash = Column(String(64), nullable=True)
    watcher_metadata = Column(JSON, nullable=True)


class KnowledgeEvent(Base, UUIDMixin, TimestampMixin):
    """Replay metadata for bounded watcher, index, and editor event streams."""

    __tablename__ = "knowledge_events"
    __table_args__ = (
        UniqueConstraint("vault_id", "event_id", name="uq_event_vault_id"),
        Index("ix_events_vault_created", "vault_id", "created_at"),
    )

    event_id = Column(String(255), nullable=False)
    vault_id = Column(String(255), ForeignKey("vaults.vault_id"), nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    replay_metadata = Column(JSON, nullable=True)
