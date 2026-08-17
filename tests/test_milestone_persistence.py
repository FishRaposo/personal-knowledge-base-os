"""Persistence contracts for the additive Milestone 3/4 data model."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect

from apps.api.src.config import AppConfig
from apps.api.src.engine import KnowledgeBase
from apps.api.src.internal.vendor_core.testing import MockDatabase
from apps.api.src.models import (
    FileSnapshot,
    Flashcard,
    FlashcardReviewState,
    KnowledgeEvent,
    SavedSearch,
    Vault,
    WatcherState,
)
from apps.api.src.store import DatabaseNoteStore, InMemoryNoteStore

ROOT = Path(__file__).resolve().parents[1]


def _note(title: str) -> dict:
    slug = title.lower()
    return {
        "id": slug,
        "title": title,
        "content": f"{title} body",
        "source": f"{slug}.md",
        "links": [],
        "tags": ["scope"],
        "metadata": {},
        "content_hash": f"hash-{slug}",
        "word_count": 2,
        "chunks": [
            {
                "id": f"{slug}::0",
                "note_id": slug,
                "index": 0,
                "content": f"{title} body",
                "content_hash": f"chunk-{slug}",
                "embedding": [0.1],
            }
        ],
    }


def test_in_memory_note_store_is_namespaced_and_legacy_defaults_remain() -> None:
    store = InMemoryNoteStore()

    store.replace_all([_note("Alpha")])
    store.replace_all([_note("Beta")], vault_id="work")

    assert store.count() == 1
    assert store.get_note("alpha")["title"] == "Alpha"
    assert store.get_note("beta") is None
    assert store.count(vault_id="work") == 1
    assert store.get_note("beta", vault_id="work")["vault_id"] == "work"


def test_database_note_store_allows_same_note_and_chunk_ids_in_two_vaults() -> None:
    db = MockDatabase()
    store = DatabaseNoteStore(db.get_session)
    note = _note("Shared")

    store.replace_all([note])
    store.replace_all([note], vault_id="work")

    assert store.count() == 1
    assert store.count(vault_id="work") == 1
    assert store.get_note("shared")["vault_id"] == "default"
    assert store.get_note("shared", vault_id="work")["vault_id"] == "work"


def test_milestone_models_round_trip_in_sqlite() -> None:
    db = MockDatabase()
    session = next(db.get_session())
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    try:
        session.add_all(
            [
                Vault(vault_id="work", name="Work", vault_metadata={"color": "blue"}),
                FileSnapshot(
                    vault_id="work",
                    relative_path="notes/a.md",
                    content_hash="a" * 64,
                    size_bytes=12,
                    modified_ns=123,
                ),
                SavedSearch(
                    saved_search_id="daily",
                    vault_id="work",
                    name="Daily",
                    query="today",
                    tags=["journal"],
                    search_mode="hybrid",
                ),
                Flashcard(
                    flashcard_id="card-a",
                    vault_id="work",
                    note_id="a",
                    prompt="Question?",
                    answer="Answer.",
                    source_citations=[{"note_id": "a", "chunk_id": "a::0"}],
                ),
                FlashcardReviewState(
                    flashcard_id="card-a",
                    vault_id="work",
                    due_at=now,
                    interval_days=1,
                    ease_factor=2.5,
                    repetitions=0,
                ),
                WatcherState(
                    vault_id="work",
                    running=False,
                    last_event_id="event-1",
                    scan_hash="scan-a",
                ),
                KnowledgeEvent(
                    event_id="event-1",
                    vault_id="work",
                    event_type="index_completed",
                    payload={"indexed": 1},
                ),
            ]
        )
        session.commit()

        assert session.query(Vault).filter_by(vault_id="work").one().name == "Work"
        assert session.query(FileSnapshot).one().relative_path == "notes/a.md"
        assert session.query(SavedSearch).one().tags == ["journal"]
        assert session.query(Flashcard).one().source_citations[0]["note_id"] == "a"
        assert session.query(FlashcardReviewState).one().interval_days == 1
        assert session.query(WatcherState).one().last_event_id == "event-1"
        assert session.query(KnowledgeEvent).one().payload == {"indexed": 1}
    finally:
        session.close()


def test_alembic_head_contains_milestone_tables_and_vault_scope(tmp_path: Path) -> None:
    database = tmp_path / "milestones.db"
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    from sqlalchemy import create_engine

    schema = inspect(create_engine(f"sqlite:///{database.as_posix()}"))
    expected = {
        "vaults",
        "notes",
        "note_chunks",
        "file_snapshots",
        "saved_searches",
        "flashcards",
        "flashcard_review_state",
        "watcher_state",
        "knowledge_events",
    }
    assert expected <= set(schema.get_table_names())
    assert "vault_id" in {column["name"] for column in schema.get_columns("notes")}
    assert "vault_id" in {
        column["name"] for column in schema.get_columns("note_chunks")
    }


def test_milestone_migration_downgrades_to_legacy_schema(tmp_path: Path) -> None:
    database = tmp_path / "downgrade.db"
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    for target in ("head", "0001_initial"):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "upgrade" if target == "head" else "downgrade",
                target,
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    from sqlalchemy import create_engine

    schema = inspect(create_engine(f"sqlite:///{database.as_posix()}"))
    assert "vaults" not in schema.get_table_names()
    assert "vault_id" not in {column["name"] for column in schema.get_columns("notes")}


def test_sqlite_runtime_state_survives_engine_restart(tmp_path: Path) -> None:
    database = tmp_path / "runtime.db"
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("# Note\nDurable local knowledge.", encoding="utf-8")
    config = AppConfig(DATABASE_URL=f"sqlite:///{database.as_posix()}")

    first = KnowledgeBase(config=config)
    first.register_vault("work", str(vault), name="Work")
    first.index_vault(str(vault), vault_id="work", incremental=True)
    saved = first.save_search(name="Daily", query="knowledge", vault_id="work")
    card = first.generate_flashcards(vault_id="work")[0]
    first.review_flashcard(card["id"], rating=4, vault_id="work")
    first.events.publish("note_changed", vault_id="work", data={"note_id": "note"})
    first.stop_watcher("work")
    snapshots = dict(first._state("work").snapshots)

    second = KnowledgeBase(config=config)

    assert second.vault_metadata("work")["path"] == str(vault.resolve())
    assert second.list_saved_searches(vault_id="work") == [saved]
    restored = second.flashcards.list(vault_id="work")
    assert restored[0]["id"] == card["id"]
    assert restored[0]["review"]["repetitions"] == 1
    assert second.events.replay(vault_id="work")[-1]["type"] == "note_changed"
    assert second._state("work").snapshots == snapshots


def test_sqlite_saved_search_name_replacement_is_durable(tmp_path: Path) -> None:
    database = tmp_path / "runtime.db"
    vault = tmp_path / "vault"
    vault.mkdir()
    config = AppConfig(DATABASE_URL=f"sqlite:///{database.as_posix()}")
    first = KnowledgeBase(config=config)
    first.register_vault("work", str(vault))

    original = first.save_search(name="Daily", query="old", vault_id="work")
    replacement = first.save_search(
        name="Daily", query="new", mode="hybrid", vault_id="work"
    )

    assert replacement["id"] != original["id"]
    assert first.list_saved_searches(vault_id="work") == [replacement]
    restarted = KnowledgeBase(config=config)
    assert restarted.list_saved_searches(vault_id="work") == [replacement]
