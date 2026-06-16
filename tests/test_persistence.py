"""Persistence tests: in-memory and SQLite-backed note stores.

Uses ``shared_core.testing.MockDatabase`` (in-memory SQLite with the schema
created) so persistence is exercised with NO real database.
"""

from shared_core.testing import MockDatabase

from apps.api.src.store import DatabaseNoteStore, InMemoryNoteStore


def _notes():
    return [
        {
            "id": "alpha",
            "title": "Alpha",
            "content": "Alpha body [[Beta]]",
            "source": "alpha.md",
            "links": ["Beta"],
            "tags": ["core"],
            "metadata": {"title": "Alpha"},
            "content_hash": "h1",
            "word_count": 2,
            "chunks": [
                {
                    "id": "alpha::0",
                    "note_id": "alpha",
                    "index": 0,
                    "content": "Alpha body",
                    "content_hash": "c1",
                    "embedding": [0.1, 0.2],
                }
            ],
        },
        {
            "id": "beta",
            "title": "Beta",
            "content": "Beta body",
            "source": "beta.md",
            "links": [],
            "tags": [],
            "metadata": {},
            "content_hash": "h2",
            "word_count": 2,
            "chunks": [],
        },
    ]


class TestInMemoryNoteStore:
    def test_replace_all_and_count(self):
        store = InMemoryNoteStore()
        assert store.replace_all(_notes()) == 2
        assert store.count() == 2

    def test_get_note(self):
        store = InMemoryNoteStore()
        store.replace_all(_notes())
        note = store.get_note("alpha")
        assert note is not None
        assert note["title"] == "Alpha"
        assert note["tags"] == ["core"]

    def test_missing_note_returns_none(self):
        store = InMemoryNoteStore()
        store.replace_all(_notes())
        assert store.get_note("nope") is None

    def test_list_sorted(self):
        store = InMemoryNoteStore()
        store.replace_all(_notes())
        ids = [n["id"] for n in store.list_notes()]
        assert ids == ["alpha", "beta"]


class TestDatabaseNoteStore:
    def _store(self):
        db = MockDatabase()
        return DatabaseNoteStore(db.get_session)

    def test_replace_all_persists(self):
        store = self._store()
        assert store.replace_all(_notes()) == 2
        assert store.count() == 2

    def test_round_trip_note(self):
        store = self._store()
        store.replace_all(_notes())
        note = store.get_note("alpha")
        assert note is not None
        assert note["title"] == "Alpha"
        assert note["links"] == ["Beta"]
        assert note["tags"] == ["core"]
        assert note["chunks"][0]["embedding"] == [0.1, 0.2]

    def test_replace_all_is_idempotent(self):
        store = self._store()
        store.replace_all(_notes())
        store.replace_all(_notes())  # must not raise on unique constraints
        assert store.count() == 2

    def test_upsert_single(self):
        store = self._store()
        store.replace_all(_notes())
        updated = _notes()[0]
        updated["title"] = "Alpha v2"
        store.upsert(updated)
        assert store.get_note("alpha")["title"] == "Alpha v2"
        assert store.count() == 2

    def test_list_notes(self):
        store = self._store()
        store.replace_all(_notes())
        assert {n["id"] for n in store.list_notes()} == {"alpha", "beta"}
