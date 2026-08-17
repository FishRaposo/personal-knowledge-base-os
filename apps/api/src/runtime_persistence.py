"""Optional SQLite persistence for local Milestone 3/4 runtime state."""

# SQLAlchemy's legacy declarative ``Column`` attributes in ``models.py`` are
# runtime descriptors but are not ``Mapped``-annotated. Keep the type-checker
# exceptions local to this adapter instead of weakening the project config.
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# pyright: reportCallIssue=false, reportReturnType=false

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .internal.vendor_core.database import Base
from .models import (
    FileSnapshot,
    Flashcard,
    FlashcardReviewState,
    KnowledgeEvent,
    SavedSearch,
    Vault,
    WatcherState,
)


class SQLiteRuntimePersistence:
    """Persist additive local-productivity state when SQLite is configured.

    The normal PostgreSQL and offline defaults are untouched. This adapter is
    activated only for an explicit ``sqlite:///`` URL and uses the same models
    as Alembic so migrations and runtime storage stay aligned.
    """

    def __init__(self, database_url: str) -> None:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("SQLite runtime persistence requires sqlite:///")
        database_path = database_url.removeprefix("sqlite:///")
        if database_path and database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(database_url)
        Base.metadata.create_all(self._engine)
        self._session = sessionmaker(bind=self._engine, expire_on_commit=False)

    def load_vaults(self) -> list[Dict[str, Any]]:
        with self._session() as session:
            rows = session.query(Vault).order_by(Vault.vault_id).all()
            return [
                {
                    "id": row.vault_id,
                    "name": row.name,
                    "path": row.root_path,
                }
                for row in rows
            ]

    def save_vault(self, vault: Dict[str, Any]) -> None:
        with self._session() as session:
            row = session.query(Vault).filter_by(vault_id=vault["id"]).one_or_none()
            if row is None:
                row = Vault(vault_id=vault["id"], name=vault["name"])
                session.add(row)
            row.name = vault["name"]
            row.root_path = vault.get("path")
            session.commit()

    def load_snapshots(self, vault_id: str) -> Dict[str, tuple[str, str]]:
        with self._session() as session:
            rows = (
                session.query(FileSnapshot)
                .filter_by(vault_id=vault_id)
                .order_by(FileSnapshot.relative_path)
                .all()
            )
            return {
                row.relative_path: (
                    str((row.snapshot_metadata or {}).get("note_id", "")),
                    row.content_hash,
                )
                for row in rows
            }

    def save_snapshots(
        self, vault_id: str, snapshots: Dict[str, tuple[str, str]]
    ) -> None:
        with self._session() as session:
            session.query(FileSnapshot).filter_by(vault_id=vault_id).delete()
            for relative_path, (note_id, content_hash) in sorted(snapshots.items()):
                session.add(
                    FileSnapshot(
                        vault_id=vault_id,
                        relative_path=relative_path,
                        content_hash=content_hash,
                        size_bytes=0,
                        snapshot_metadata={"note_id": note_id},
                    )
                )
            session.commit()

    def load_saved_searches(self) -> list[Dict[str, Any]]:
        with self._session() as session:
            rows = (
                session.query(SavedSearch)
                .order_by(SavedSearch.vault_id, SavedSearch.saved_search_id)
                .all()
            )
            return [
                {
                    "id": row.saved_search_id,
                    "vault_id": row.vault_id,
                    "name": row.name,
                    "query": row.query,
                    "mode": row.search_mode,
                    "tags": list(row.tags or []),
                }
                for row in rows
            ]

    def save_search(self, saved: Dict[str, Any]) -> None:
        with self._session() as session:
            row = (
                session.query(SavedSearch)
                .filter_by(vault_id=saved["vault_id"], saved_search_id=saved["id"])
                .one_or_none()
            )
            if row is None:
                row = SavedSearch(
                    vault_id=saved["vault_id"], saved_search_id=saved["id"]
                )
                session.add(row)
            row.name = saved["name"]
            row.query = saved["query"]
            row.search_mode = saved["mode"]
            row.tags = list(saved.get("tags", []))
            session.commit()

    def delete_search(self, vault_id: str, search_id: str) -> None:
        with self._session() as session:
            (
                session.query(SavedSearch)
                .filter_by(vault_id=vault_id, saved_search_id=search_id)
                .delete()
            )
            session.commit()

    def load_cards(self) -> list[Dict[str, Any]]:
        with self._session() as session:
            reviews = {
                (row.vault_id, row.flashcard_id): row
                for row in session.query(FlashcardReviewState).all()
            }
            cards: list[Dict[str, Any]] = []
            for row in (
                session.query(Flashcard)
                .order_by(Flashcard.vault_id, Flashcard.flashcard_id)
                .all()
            ):
                citations = list(row.source_citations or [])
                citation = citations[0] if citations else {}
                review = reviews.get((row.vault_id, row.flashcard_id))
                metadata = dict(row.card_metadata or {})
                cards.append(
                    {
                        "id": row.flashcard_id,
                        "vault_id": row.vault_id,
                        "question": row.prompt,
                        "answer": row.answer,
                        "citation": citation,
                        "review": {
                            "repetitions": review.repetitions if review else 0,
                            "interval_days": review.interval_days if review else 0,
                            "due_in_days": review.interval_days if review else 0,
                            "ease": review.ease_factor if review else 2.5,
                        },
                        "enriched": bool(metadata.get("enriched", False)),
                    }
                )
            return cards

    def save_cards(self, cards: Iterable[Dict[str, Any]]) -> None:
        with self._session() as session:
            for card in cards:
                key = {
                    "vault_id": card["vault_id"],
                    "flashcard_id": card["id"],
                }
                row = session.query(Flashcard).filter_by(**key).one_or_none()
                if row is None:
                    row = Flashcard(note_id=card["citation"].get("note_id"), **key)
                    session.add(row)
                row.note_id = card["citation"].get("note_id")
                row.prompt = card["question"]
                row.answer = card["answer"]
                row.source_citations = [deepcopy(card["citation"])]
                row.card_metadata = {"enriched": bool(card.get("enriched", False))}

                review_data = card.get("review", {})
                review = (
                    session.query(FlashcardReviewState).filter_by(**key).one_or_none()
                )
                if review is None:
                    from datetime import datetime, timezone

                    review = FlashcardReviewState(
                        due_at=datetime.now(timezone.utc), **key
                    )
                    session.add(review)
                review.interval_days = int(review_data.get("interval_days", 0))
                review.ease_factor = float(review_data.get("ease", 2.5))
                review.repetitions = int(review_data.get("repetitions", 0))
            session.commit()

    def load_events(self) -> list[Dict[str, Any]]:
        with self._session() as session:
            rows = session.query(KnowledgeEvent).all()
            events = [
                {
                    "id": row.event_id,
                    "type": row.event_type,
                    "vault_id": row.vault_id,
                    "data": dict(row.payload or {}),
                }
                for row in rows
            ]
            return sorted(events, key=lambda event: int(event["id"]))

    def save_event(self, event: Dict[str, Any]) -> None:
        with self._session() as session:
            exists = (
                session.query(KnowledgeEvent)
                .filter_by(vault_id=event["vault_id"], event_id=event["id"])
                .one_or_none()
            )
            if exists is None:
                session.add(
                    KnowledgeEvent(
                        event_id=event["id"],
                        vault_id=event["vault_id"],
                        event_type=event["type"],
                        payload=dict(event.get("data", {})),
                    )
                )
                session.commit()

    def save_watcher(self, vault_id: str, *, running: bool, backend: str) -> None:
        with self._session() as session:
            row = session.query(WatcherState).filter_by(vault_id=vault_id).one_or_none()
            if row is None:
                row = WatcherState(vault_id=vault_id)
                session.add(row)
            # A process cannot restore a live thread; persisted state is metadata.
            row.running = running
            row.watcher_metadata = {"backend": backend}
            session.commit()


def sqlite_runtime_persistence(database_url: str) -> SQLiteRuntimePersistence | None:
    """Return the opt-in adapter without touching non-SQLite defaults."""
    if not database_url.startswith("sqlite:///"):
        return None
    return SQLiteRuntimePersistence(database_url)
