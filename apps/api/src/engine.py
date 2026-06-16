"""KnowledgeBase: the orchestration layer wiring ingestion, graph, and retrieval.

Holds the active note store, vector store, backlinks graph, and embedder, and
exposes the operations the API and worker share: ``index`` a vault, ``search``
(keyword or semantic), ``chat`` (RAG with cited answers), plus graph/backlinks/tag
accessors. Offline-first: with no database and no API key it uses an in-memory
note store, an in-memory vector store, and the deterministic embedder/sim-LLM.
"""

from typing import Dict, List, Optional

from shared_core.vectorstore import InMemoryVectorStore, VectorStore

from .chat import chat_with_citations
from .config import AppConfig
from .embeddings import EmbeddingGenerator
from .graph import BacklinksGraph
from .indexer import NotesIndexer
from .search import build_vector_store, keyword_search, semantic_search
from .store import InMemoryNoteStore, NoteStore


class KnowledgeBase:
    """In-process knowledge-base engine over a markdown vault."""

    def __init__(
        self,
        *,
        config: Optional[AppConfig] = None,
        note_store: Optional[NoteStore] = None,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[EmbeddingGenerator] = None,
        api_keys: Optional[Dict[str, Optional[str]]] = None,
    ) -> None:
        self.config = config or AppConfig()
        self.note_store = note_store or InMemoryNoteStore()
        self.vector_store = vector_store or InMemoryVectorStore()
        self.embedder = embedder or EmbeddingGenerator(
            offline=self.config.EMBEDDINGS_OFFLINE,
            api_key=_secret(self.config.OPENAI_API_KEY),
            model=self.config.LLM_EMBEDDING_MODEL,
        )
        self.api_keys = api_keys or _api_keys_from_config(self.config)
        self.graph = BacklinksGraph()
        self.indexer = NotesIndexer(
            chunk_size=self.config.CHUNK_SIZE,
            chunk_overlap=self.config.CHUNK_OVERLAP,
        )

    # ------------------------------------------------------------------ #
    # Ingestion
    # ------------------------------------------------------------------ #
    def index_vault(self, path: str) -> Dict:
        """Parse, embed, persist, and graph every note under ``path``."""
        notes = self.indexer.parse_directory(path)
        return self._load(notes, path=path)

    def index_notes(self, notes: List[Dict]) -> Dict:
        """Index already-parsed note dicts (used by tests/workers)."""
        return self._load(notes, path=None)

    def _load(self, notes: List[Dict], *, path: Optional[str]) -> Dict:
        self.embedder.embed_chunks(
            [chunk for note in notes for chunk in note.get("chunks", [])]
        )
        self.note_store.replace_all(notes)
        build_vector_store(notes, self.embedder, self.vector_store)
        self.graph.build_graph(notes)
        return {
            "indexed_path": path,
            "total_notes": len(notes),
            "total_chunks": sum(len(n.get("chunks", [])) for n in notes),
            "total_links": sum(len(n.get("links", [])) for n in notes),
            "total_tags": len(self.list_tags()),
        }

    def reindex_from_store(self) -> None:
        """Rebuild the in-memory graph + vector store from persisted notes.

        Called on startup when notes were loaded from the database in a prior run
        so search and the graph work immediately without re-parsing the vault.
        """
        notes = self.note_store.list_notes()
        if not notes:
            return
        for note in notes:
            if not note.get("chunks"):
                continue
            if note["chunks"][0].get("embedding") is None:
                self.embedder.embed_chunks(note["chunks"])
        build_vector_store(notes, self.embedder, self.vector_store)
        self.graph.build_graph(notes)

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #
    def search(
        self, query: str, limit: int = 5, *, mode: str = "keyword"
    ) -> List[Dict]:
        """Search notes by ``keyword`` (default), ``semantic``, or ``hybrid``."""
        notes = self.note_store.list_notes()
        if mode == "semantic":
            return semantic_search(
                notes, query, limit, embedder=self.embedder, store=self.vector_store
            )
        if mode == "hybrid":
            return self._hybrid(notes, query, limit)
        return keyword_search(notes, query, limit)

    def _hybrid(self, notes: List[Dict], query: str, limit: int) -> List[Dict]:
        """Merge keyword + semantic results, de-duplicated by note id."""
        merged: Dict[str, Dict] = {}
        for result in keyword_search(notes, query, limit):
            merged[result["id"]] = result
        for result in semantic_search(
            notes, query, limit, embedder=self.embedder, store=self.vector_store
        ):
            if result["id"] not in merged:
                merged[result["id"]] = result
        ranked = sorted(merged.values(), key=lambda r: r["score"], reverse=True)
        return ranked[:limit]

    def chat(self, query: str, *, limit: int = 3) -> Dict:
        """Retrieve top notes (semantic) and answer with cited grounding."""
        notes = self.note_store.list_notes()
        retrieved = semantic_search(
            notes, query, limit, embedder=self.embedder, store=self.vector_store
        )
        if not retrieved:
            retrieved = keyword_search(notes, query, limit)
        return chat_with_citations(
            query,
            retrieved,
            model=self.config.CHAT_MODEL,
            api_keys=self.api_keys,
        )

    # ------------------------------------------------------------------ #
    # Graph / metadata accessors
    # ------------------------------------------------------------------ #
    def get_note(self, note_id: str) -> Optional[Dict]:
        return self.note_store.get_note(note_id)

    def get_backlinks(self, note_id: str) -> List[str]:
        return self.graph.get_backlinks(note_id)

    def get_graph(self) -> Dict:
        return self.graph.get_graph()

    def list_tags(self) -> List[Dict]:
        """Return tag -> note-count rollup across all indexed notes."""
        counts: Dict[str, int] = {}
        notes_by_tag: Dict[str, List[str]] = {}
        for note in self.note_store.list_notes():
            for tag in note.get("tags", []):
                counts[tag] = counts.get(tag, 0) + 1
                notes_by_tag.setdefault(tag, []).append(note["id"])
        return [
            {"tag": tag, "count": counts[tag], "notes": notes_by_tag[tag]}
            for tag in sorted(counts)
        ]

    def stats(self) -> Dict:
        notes = self.note_store.list_notes()
        return {
            "total_notes": len(notes),
            "total_chunks": self.vector_store.count(),
            "total_tags": len(self.list_tags()),
        }


def _secret(value) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        return value.get_secret_value()
    return value


def _api_keys_from_config(config: AppConfig) -> Dict[str, Optional[str]]:
    return {
        "openai": _secret(config.OPENAI_API_KEY),
        "anthropic": _secret(config.ANTHROPIC_API_KEY),
    }
