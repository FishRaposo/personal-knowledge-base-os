"""Note persistence: in-memory (offline default) and database-backed stores.

Both implement the same ``NoteStore`` surface so the API and worker swap backends
without code changes. ``InMemoryNoteStore`` keeps everything in dicts (tests + the
offline demo). ``DatabaseNoteStore`` upserts notes/chunks into PostgreSQL via a
internal vendored session factory so the index survives restarts.
"""

from typing import Callable, Dict, List, Optional

from .models import Note as NoteModel
from .models import NoteChunk as NoteChunkModel
from .models import Vault as VaultModel


def _note_to_dict(note: Dict, vault_id: str = "default") -> Dict:
    """Shallow copy of an indexer note dict (without embeddings on chunks)."""
    return {
        "id": note["id"],
        "vault_id": note.get("vault_id", vault_id),
        "title": note["title"],
        "content": note["content"],
        "source": note.get("source"),
        "links": list(note.get("links", [])),
        "tags": list(note.get("tags", [])),
        "metadata": dict(note.get("metadata", {})),
        "content_hash": note.get("content_hash", ""),
        "word_count": note.get("word_count", 0),
        "chunks": note.get("chunks", []),
    }


class NoteStore:
    """Abstract note store interface."""

    def replace_all(
        self, notes: List[Dict], vault_id: str = "default"
    ) -> int:  # pragma: no cover - interface
        raise NotImplementedError

    def list_notes(
        self, vault_id: str = "default"
    ) -> List[Dict]:  # pragma: no cover - interface
        raise NotImplementedError

    def get_note(
        self, note_id: str, vault_id: str = "default"
    ) -> Optional[Dict]:  # pragma: no cover
        raise NotImplementedError

    def count(self, vault_id: str = "default") -> int:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryNoteStore(NoteStore):
    """Dict-backed note store — the offline/testing default."""

    def __init__(self) -> None:
        self._notes: Dict[str, Dict[str, Dict]] = {}

    def replace_all(self, notes: List[Dict], vault_id: str = "default") -> int:
        self._notes[vault_id] = {
            note["id"]: _note_to_dict(note, vault_id) for note in notes
        }
        return len(self._notes[vault_id])

    def upsert(self, note: Dict, vault_id: str = "default") -> None:
        self._notes.setdefault(vault_id, {})[note["id"]] = _note_to_dict(note, vault_id)

    def list_notes(self, vault_id: str = "default") -> List[Dict]:
        notes = self._notes.get(vault_id, {})
        return [notes[key] for key in sorted(notes)]

    def get_note(self, note_id: str, vault_id: str = "default") -> Optional[Dict]:
        return self._notes.get(vault_id, {}).get(note_id)

    def count(self, vault_id: str = "default") -> int:
        return len(self._notes.get(vault_id, {}))


class DatabaseNoteStore(NoteStore):
    """PostgreSQL-backed note store using the internal session factory."""

    def __init__(self, session_factory: Callable):
        # ``session_factory`` is ``DatabaseManager.get_session`` (a generator fn).
        self._session_factory = session_factory

    def _session(self):
        return next(self._session_factory())

    def replace_all(self, notes: List[Dict], vault_id: str = "default") -> int:
        session = self._session()
        try:
            self._ensure_vault(session, vault_id)
            session.query(NoteChunkModel).filter_by(vault_id=vault_id).delete()
            session.query(NoteModel).filter_by(vault_id=vault_id).delete()
            for note in notes:
                self._insert(session, note, vault_id)
            session.commit()
            return len(notes)
        finally:
            session.close()

    def upsert(self, note: Dict, vault_id: str = "default") -> None:
        session = self._session()
        try:
            self._ensure_vault(session, vault_id)
            session.query(NoteChunkModel).filter_by(
                vault_id=vault_id, note_id=note["id"]
            ).delete()
            session.query(NoteModel).filter_by(
                vault_id=vault_id, note_id=note["id"]
            ).delete()
            self._insert(session, note, vault_id)
            session.commit()
        finally:
            session.close()

    def _ensure_vault(self, session, vault_id: str) -> None:
        if session.query(VaultModel).filter_by(vault_id=vault_id).first() is None:
            session.add(VaultModel(vault_id=vault_id, name=vault_id))
            session.flush()

    def _insert(self, session, note: Dict, vault_id: str = "default") -> None:
        session.add(
            NoteModel(
                vault_id=vault_id,
                note_id=note["id"],
                title=note["title"],
                source=note.get("source"),
                content=note["content"],
                content_hash=note.get("content_hash", ""),
                word_count=note.get("word_count", 0),
                links=list(note.get("links", [])),
                tags=list(note.get("tags", [])),
                note_metadata=dict(note.get("metadata", {})),
            )
        )
        for chunk in note.get("chunks", []):
            session.add(
                NoteChunkModel(
                    vault_id=vault_id,
                    chunk_id=chunk["id"],
                    note_id=note["id"],
                    chunk_index=chunk.get("index", 0),
                    content=chunk.get("content", ""),
                    content_hash=chunk.get("content_hash"),
                    embedding=chunk.get("embedding"),
                )
            )

    def list_notes(self, vault_id: str = "default") -> List[Dict]:
        session = self._session()
        try:
            rows = (
                session.query(NoteModel)
                .filter_by(vault_id=vault_id)
                .order_by(NoteModel.note_id)
                .all()
            )
            return [self._row_to_dict(session, row) for row in rows]
        finally:
            session.close()

    def get_note(self, note_id: str, vault_id: str = "default") -> Optional[Dict]:
        session = self._session()
        try:
            row = (
                session.query(NoteModel)
                .filter_by(vault_id=vault_id, note_id=note_id)
                .first()
            )
            return self._row_to_dict(session, row) if row else None
        finally:
            session.close()

    def count(self, vault_id: str = "default") -> int:
        session = self._session()
        try:
            return session.query(NoteModel).filter_by(vault_id=vault_id).count()
        finally:
            session.close()

    def _row_to_dict(self, session, row: NoteModel) -> Dict:
        chunks = (
            session.query(NoteChunkModel)
            .filter_by(vault_id=row.vault_id, note_id=row.note_id)
            .order_by(NoteChunkModel.chunk_index)
            .all()
        )
        return {
            "id": row.note_id,
            "vault_id": row.vault_id,
            "title": row.title,
            "content": row.content,
            "source": row.source,
            "links": row.links or [],
            "tags": row.tags or [],
            "metadata": row.note_metadata or {},
            "content_hash": row.content_hash,
            "word_count": row.word_count,
            "chunks": [
                {
                    "id": chunk.chunk_id,
                    "note_id": chunk.note_id,
                    "index": chunk.chunk_index,
                    "content": chunk.content,
                    "content_hash": chunk.content_hash,
                    "embedding": chunk.embedding,
                }
                for chunk in chunks
            ],
        }
