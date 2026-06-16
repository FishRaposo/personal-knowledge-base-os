import os
import sys

sys.path.insert(0, os.path.abspath("."))
from shared_core.testing import MockDatabase

from apps.api.src.engine import KnowledgeBase
from apps.api.src.store import DatabaseNoteStore

db = MockDatabase()
store = DatabaseNoteStore(db.get_session)
kb = KnowledgeBase(note_store=store)
summary = kb.index_vault("demo_vault")
print("indexed:", summary["total_notes"], "into DB-backed store")

# Simulate a fresh process: new engine reading from the same DB store, rebuild index.
kb2 = KnowledgeBase(note_store=DatabaseNoteStore(db.get_session))
kb2.reindex_from_store()
print("persisted notes survive:", kb2.note_store.count())
print(
    "semantic search works after reload:",
    bool(kb2.search("embeddings", mode="semantic")),
)
print("backlinks after reload:", kb2.get_backlinks("notes_architecture")[:3])
assert kb2.note_store.count() == summary["total_notes"]
assert kb2.search("embeddings", mode="semantic")
print("DB-PERSISTENCE SMOKE: OK")
