"""Note persistence: in-memory (offline default) and database-backed stores.

Both implement the same ``NoteStore`` surface so the API and worker swap backends
without code changes. ``InMemoryNoteStore`` keeps everything in dicts (tests + the
offline demo). ``DatabaseNoteStore`` upserts notes/chunks into PostgreSQL via a
``shared_core`` session factory so the index survives restarts.
"""

from typing import Callable, Dict, List, Optional

from .models import Note as NoteModel
from .models import NoteChunk as NoteChunkModel


def _note_to_dict(note: Dict) -> Dict:
    """Shallow copy of an indexer note dict (without embeddings on chunks)."""
    return {
        "id": note["id"],
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

    def replace_all(self, notes: List[Dict]) -> int:  # pragma: no cover - interface
        raise NotImplementedError

    def list_notes(self) -> List[Dict]:  # pragma: no cover - interface
        raise NotImplementedError

    def get_note(self, note_id: str) -> Optional[Dict]:  # pragma: no cover
        raise NotImplementedError

    def count(self) -> int:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryNoteStore(NoteStore):
    """Dict-backed note store — the offline/testing default."""

    def __init__(self) -> None:
        self._notes: Dict[str, Dict] = {}

    def replace_all(self, notes: List[Dict]) -> int:
        self._notes = {note["id"]: _note_to_dict(note) for note in notes}
        return len(self._notes)

    def upsert(self, note: Dict) -> None:
        self._notes[note["id"]] = _note_to_dict(note)

    def list_notes(self) -> List[Dict]:
        return [self._notes[key] for key in sorted(self._notes)]

    def get_note(self, note_id: str) -> Optional[Dict]:
        return self._notes.get(note_id)

    def count(self) -> int:
        return len(self._notes)


class DatabaseNoteStore(NoteStore):
    """PostgreSQL-backed note store using a ``shared_core`` session factory."""

    def __init__(self, session_factory: Callable):
        # ``session_factory`` is ``DatabaseManager.get_session`` (a generator fn).
        self._session_factory = session_factory

    def _session(self):
        return next(self._session_factory())

    def replace_all(self, notes: List[Dict]) -> int:
        session = self._session()
        try:
            session.query(NoteChunkModel).delete()
            session.query(NoteModel).delete()
            for note in notes:
                self._insert(session, note)
            session.commit()
            return len(notes)
        finally:
            session.close()

    def upsert(self, note: Dict) -> None:
        session = self._session()
        try:
            session.query(NoteChunkModel).filter_by(note_id=note["id"]).delete()
            session.query(NoteModel).filter_by(note_id=note["id"]).delete()
            self._insert(session, note)
            session.commit()
        finally:
            session.close()

    def _insert(self, session, note: Dict) -> None:
        session.add(
            NoteModel(
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
                    chunk_id=chunk["id"],
                    note_id=note["id"],
                    chunk_index=chunk.get("index", 0),
                    content=chunk.get("content", ""),
                    content_hash=chunk.get("content_hash"),
                    embedding=chunk.get("embedding"),
                )
            )

    def list_notes(self) -> List[Dict]:
        session = self._session()
        try:
            rows = session.query(NoteModel).order_by(NoteModel.note_id).all()
            return [self._row_to_dict(session, row) for row in rows]
        finally:
            session.close()

    def get_note(self, note_id: str) -> Optional[Dict]:
        session = self._session()
        try:
            row = session.query(NoteModel).filter_by(note_id=note_id).first()
            return self._row_to_dict(session, row) if row else None
        finally:
            session.close()

    def count(self) -> int:
        session = self._session()
        try:
            return session.query(NoteModel).count()
        finally:
            session.close()

    def _row_to_dict(self, session, row: NoteModel) -> Dict:
        chunks = (
            session.query(NoteChunkModel)
            .filter_by(note_id=row.note_id)
            .order_by(NoteChunkModel.chunk_index)
            .all()
        )
        return {
            "id": row.note_id,
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
