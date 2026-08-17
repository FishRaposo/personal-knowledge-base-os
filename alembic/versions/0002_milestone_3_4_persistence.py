"""Add vault scoping and Milestone 3/4 local persistence.

Revision ID: 0002_milestones
Revises: 0001_initial
Create Date: 2026-08-17 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002_milestones"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    """Upgrade the legacy global note schema to vault-scoped storage."""
    op.drop_index("ix_note_chunks_chunk_id", table_name="note_chunks")
    op.drop_index("ix_note_chunks_note_id", table_name="note_chunks")
    op.drop_index("ix_note_chunks_content_hash", table_name="note_chunks")
    op.drop_index("ix_notes_note_id", table_name="notes")
    op.drop_index("ix_notes_content_hash", table_name="notes")
    op.rename_table("note_chunks", "note_chunks_legacy")
    op.rename_table("notes", "notes_legacy")

    op.create_table(
        "vaults",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vault_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("root_path", sa.String(length=2000), nullable=True),
        sa.Column("vault_metadata", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_vaults"),
        sa.UniqueConstraint("vault_id", name="uq_vaults_vault_id"),
    )
    op.create_index("ix_vaults_vault_id", "vaults", ["vault_id"], unique=True)
    op.execute(
        sa.text(
            "INSERT INTO vaults "
            "(id, vault_id, name, root_path, vault_metadata, created_at, updated_at) "
            "VALUES (:id, 'default', 'Default', NULL, NULL, :created, :updated)"
        ).bindparams(
            id="00000000-0000-0000-0000-000000000001",
            created="2026-08-17 00:00:00+00:00",
            updated="2026-08-17 00:00:00+00:00",
        )
    )

    op.create_table(
        "notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "vault_id", sa.String(length=255), server_default="default", nullable=False
        ),
        sa.Column("note_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=1000), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("links", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("note_metadata", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["vault_id"], ["vaults.vault_id"], name="fk_notes_vault"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notes_vaulted"),
        sa.UniqueConstraint("vault_id", "note_id", name="uq_notes_vault_note"),
    )
    op.create_index("ix_notes_vault_id", "notes", ["vault_id"], unique=False)
    op.create_index("ix_notes_note_id", "notes", ["note_id"], unique=False)
    op.create_index(
        "ix_notes_vault_note", "notes", ["vault_id", "note_id"], unique=False
    )
    op.create_index("ix_notes_content_hash", "notes", ["content_hash"], unique=False)
    op.execute(
        "INSERT INTO notes "
        "(id, vault_id, note_id, title, source, content, content_hash, word_count, "
        "links, tags, note_metadata, created_at, updated_at) "
        "SELECT id, 'default', note_id, title, source, content, content_hash, "
        "word_count, links, tags, note_metadata, created_at, updated_at "
        "FROM notes_legacy"
    )

    op.create_table(
        "note_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "vault_id", sa.String(length=255), server_default="default", nullable=False
        ),
        sa.Column("chunk_id", sa.String(length=512), nullable=False),
        sa.Column("note_id", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["vault_id"], ["vaults.vault_id"], name="fk_chunks_vault"
        ),
        sa.ForeignKeyConstraint(
            ["vault_id", "note_id"],
            ["notes.vault_id", "notes.note_id"],
            name="fk_note_chunks_vault_note",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_note_chunks_vaulted"),
        sa.UniqueConstraint("vault_id", "chunk_id", name="uq_chunks_vault_chunk"),
    )
    op.create_index(
        "ix_note_chunks_vault_id", "note_chunks", ["vault_id"], unique=False
    )
    op.create_index(
        "ix_note_chunks_chunk_id", "note_chunks", ["chunk_id"], unique=False
    )
    op.create_index("ix_note_chunks_note_id", "note_chunks", ["note_id"], unique=False)
    op.create_index(
        "ix_chunks_vault_note", "note_chunks", ["vault_id", "note_id"], unique=False
    )
    op.create_index(
        "ix_note_chunks_content_hash", "note_chunks", ["content_hash"], unique=False
    )
    op.execute(
        "INSERT INTO note_chunks "
        "(id, vault_id, chunk_id, note_id, chunk_index, content, content_hash, "
        "embedding, created_at, updated_at) "
        "SELECT id, 'default', chunk_id, note_id, chunk_index, content, content_hash, "
        "embedding, created_at, updated_at FROM note_chunks_legacy"
    )
    op.drop_table("note_chunks_legacy")
    op.drop_table("notes_legacy")

    _create_milestone_tables()


def _create_milestone_tables() -> None:
    op.create_table(
        "file_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vault_id", sa.String(length=255), nullable=False),
        sa.Column("relative_path", sa.String(length=2000), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("modified_ns", sa.BigInteger(), nullable=True),
        sa.Column("snapshot_metadata", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["vault_id"], ["vaults.vault_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vault_id", "relative_path", name="uq_snapshot_vault_path"),
    )
    op.create_index(
        "ix_snapshot_vault_hash", "file_snapshots", ["vault_id", "content_hash"]
    )

    op.create_table(
        "saved_searches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("saved_search_id", sa.String(length=255), nullable=False),
        sa.Column("vault_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("search_mode", sa.String(length=32), nullable=False),
        sa.Column("search_metadata", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["vault_id"], ["vaults.vault_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "vault_id", "saved_search_id", name="uq_saved_search_vault_id"
        ),
        sa.UniqueConstraint("vault_id", "name", name="uq_saved_search_vault_name"),
    )

    op.create_table(
        "flashcards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("flashcard_id", sa.String(length=255), nullable=False),
        sa.Column("vault_id", sa.String(length=255), nullable=False),
        sa.Column("note_id", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("source_citations", sa.JSON(), nullable=False),
        sa.Column("card_metadata", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["vault_id"], ["vaults.vault_id"]),
        sa.ForeignKeyConstraint(
            ["vault_id", "note_id"],
            ["notes.vault_id", "notes.note_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vault_id", "flashcard_id", name="uq_flashcard_vault_id"),
    )

    op.create_table(
        "flashcard_review_state",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("flashcard_id", sa.String(length=255), nullable=False),
        sa.Column("vault_id", sa.String(length=255), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("ease_factor", sa.Float(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=False),
        sa.Column("last_rating", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["vault_id"], ["vaults.vault_id"]),
        sa.ForeignKeyConstraint(
            ["vault_id", "flashcard_id"],
            ["flashcards.vault_id", "flashcards.flashcard_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vault_id", "flashcard_id", name="uq_review_vault_card"),
    )

    op.create_table(
        "watcher_state",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vault_id", sa.String(length=255), nullable=False),
        sa.Column("running", sa.Boolean(), nullable=False),
        sa.Column("last_event_id", sa.String(length=255), nullable=True),
        sa.Column("scan_hash", sa.String(length=64), nullable=True),
        sa.Column("watcher_metadata", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["vault_id"], ["vaults.vault_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vault_id", name="uq_watcher_vault"),
    )

    op.create_table(
        "knowledge_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("vault_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("replay_metadata", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["vault_id"], ["vaults.vault_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vault_id", "event_id", name="uq_event_vault_id"),
    )
    op.create_index(
        "ix_knowledge_events_event_type", "knowledge_events", ["event_type"]
    )
    op.create_index(
        "ix_events_vault_created", "knowledge_events", ["vault_id", "created_at"]
    )


def downgrade() -> None:
    """Remove Milestone tables; retain scoped note data in the default vault."""
    op.drop_index("ix_events_vault_created", table_name="knowledge_events")
    op.drop_index("ix_knowledge_events_event_type", table_name="knowledge_events")
    op.drop_table("knowledge_events")
    op.drop_table("watcher_state")
    op.drop_table("flashcard_review_state")
    op.drop_table("flashcards")
    op.drop_table("saved_searches")
    op.drop_index("ix_snapshot_vault_hash", table_name="file_snapshots")
    op.drop_table("file_snapshots")

    for index in (
        "ix_note_chunks_vault_id",
        "ix_note_chunks_chunk_id",
        "ix_note_chunks_note_id",
        "ix_chunks_vault_note",
        "ix_note_chunks_content_hash",
    ):
        op.drop_index(index, table_name="note_chunks")
    for index in (
        "ix_notes_vault_id",
        "ix_notes_note_id",
        "ix_notes_vault_note",
        "ix_notes_content_hash",
    ):
        op.drop_index(index, table_name="notes")
    op.rename_table("note_chunks", "note_chunks_scoped")
    op.rename_table("notes", "notes_scoped")

    op.create_table(
        "notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("note_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=1000), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("links", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("note_metadata", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id"),
    )
    op.create_index("ix_notes_note_id", "notes", ["note_id"], unique=True)
    op.create_index("ix_notes_content_hash", "notes", ["content_hash"])
    op.execute(
        "INSERT INTO notes "
        "(id, note_id, title, source, content, content_hash, word_count, links, "
        "tags, note_metadata, created_at, updated_at) "
        "SELECT id, note_id, title, source, content, content_hash, word_count, "
        "links, tags, note_metadata, created_at, updated_at FROM notes_scoped "
        "WHERE vault_id = 'default'"
    )

    op.create_table(
        "note_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=512), nullable=False),
        sa.Column("note_id", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["note_id"], ["notes.note_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id"),
    )
    op.create_index("ix_note_chunks_chunk_id", "note_chunks", ["chunk_id"], unique=True)
    op.create_index("ix_note_chunks_note_id", "note_chunks", ["note_id"])
    op.create_index("ix_note_chunks_content_hash", "note_chunks", ["content_hash"])
    op.execute(
        "INSERT INTO note_chunks "
        "(id, chunk_id, note_id, chunk_index, content, content_hash, embedding, "
        "created_at, updated_at) "
        "SELECT id, chunk_id, note_id, chunk_index, content, content_hash, "
        "embedding, created_at, updated_at FROM note_chunks_scoped "
        "WHERE vault_id = 'default'"
    )

    op.drop_table("note_chunks_scoped")
    op.drop_table("notes_scoped")
    op.drop_table("vaults")
