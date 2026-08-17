"""KnowledgeBase: the orchestration layer wiring ingestion, graph, and retrieval.

Holds the active note store, vector store, backlinks graph, and embedder, and
exposes the operations the API and worker share: ``index`` a vault, ``search``
(keyword or semantic), ``chat`` (RAG with cited answers), plus graph/backlinks/tag
accessors. Offline-first: with no database and no API key it uses an in-memory
note store, an in-memory vector store, and the deterministic embedder/sim-LLM.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .chat import chat_with_citations
from .config import AppConfig
from .embeddings import EmbeddingGenerator
from .events import EventBus
from .flashcards import FlashcardService
from .graph import BacklinksGraph
from .indexer import NotesIndexer
from .internal.vendor_core.vectorstore import InMemoryVectorStore, VectorStore
from .search import build_vector_store, keyword_search, semantic_search
from .store import InMemoryNoteStore, NoteStore
from .watcher import PollingVaultWatcher


def _reject_symlink_components(path: Path, *, label: str) -> None:
    """Reject an unresolved path if any existing component is a symlink."""
    unresolved = path.absolute()
    for component in (unresolved, *unresolved.parents):
        if component.is_symlink():
            raise ValueError(f"{label} contains a symlink: {component}")


@dataclass
class _VaultState:
    note_store: NoteStore
    vector_store: VectorStore
    graph: BacklinksGraph
    root: Optional[Path] = None
    name: str = ""
    snapshots: Dict[str, str] = field(default_factory=dict)


class KnowledgeBase:
    """In-process knowledge-base engine over local markdown vaults.

    Notes can use the optional durable ``NoteStore``. Vault registrations,
    content-hash snapshots, vector/graph state, selected vault, saved searches,
    flashcards/reviews, watcher handles, and replay events are deliberately
    process-local in the offline default. The additive SQL models reserve durable
    storage for adapters without claiming those adapters are active here.
    """

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
        # Keep the unresolved configured path so a symlink alias remains visible
        # to the explicit validation performed when indexing starts.
        default_root = Path(self.config.DEFAULT_VAULT_PATH).absolute()
        self._vaults: Dict[str, _VaultState] = {
            "default": _VaultState(
                note_store=note_store or InMemoryNoteStore(),
                vector_store=vector_store or InMemoryVectorStore(),
                graph=BacklinksGraph(),
                root=default_root,
                name="Default",
            )
        }
        self.embedder = embedder or EmbeddingGenerator(
            offline=self.config.EMBEDDINGS_OFFLINE,
            api_key=_secret(self.config.OPENAI_API_KEY),
            model=self.config.LLM_EMBEDDING_MODEL,
        )
        self.api_keys = api_keys or _api_keys_from_config(self.config)
        self.events = EventBus()
        self.flashcards = FlashcardService()
        self._saved_searches: Dict[tuple[str, str], Dict] = {}
        self._watchers: Dict[str, PollingVaultWatcher] = {}
        self._selected_vault_id = "default"
        self.indexer = NotesIndexer(
            chunk_size=self.config.CHUNK_SIZE,
            chunk_overlap=self.config.CHUNK_OVERLAP,
        )

    # ------------------------------------------------------------------ #
    # Ingestion
    # ------------------------------------------------------------------ #
    @property
    def note_store(self) -> NoteStore:
        return self._vaults["default"].note_store

    @note_store.setter
    def note_store(self, value: NoteStore) -> None:
        previous = self._vaults["default"].note_store
        self._vaults["default"].note_store = value
        for vault_id, state in self._vaults.items():
            if vault_id != "default" and state.note_store is previous:
                state.note_store = value

    @property
    def vector_store(self) -> VectorStore:
        return self._vaults["default"].vector_store

    @vector_store.setter
    def vector_store(self, value: VectorStore) -> None:
        self._vaults["default"].vector_store = value

    @property
    def graph(self) -> BacklinksGraph:
        return self._vaults["default"].graph

    @graph.setter
    def graph(self, value: BacklinksGraph) -> None:
        self._vaults["default"].graph = value

    def _state(self, vault_id: str = "default") -> _VaultState:
        if vault_id not in self._vaults:
            self._vaults[vault_id] = _VaultState(
                note_store=self._vaults["default"].note_store,
                vector_store=InMemoryVectorStore(),
                graph=BacklinksGraph(),
                name=vault_id,
            )
        return self._vaults[vault_id]

    def register_vault(
        self, vault_id: str, path: str, *, name: Optional[str] = None
    ) -> Dict:
        vault_id = vault_id.strip()
        if not vault_id or any(
            char
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for char in vault_id
        ):
            raise ValueError("vault_id must contain only letters, numbers, '_' or '-'")
        raw_root = Path(path)
        _reject_symlink_components(raw_root, label="vault path")
        root = raw_root.resolve(strict=False)
        if root.exists() and not root.is_dir():
            raise ValueError("vault path must be a non-symlink directory")
        state = self._state(vault_id)
        state.root = root
        state.name = name or state.name or vault_id
        return self.vault_metadata(vault_id)

    def vault_metadata(self, vault_id: str) -> Dict:
        state = self._state(vault_id)
        return {
            "id": vault_id,
            "name": state.name or vault_id,
            "path": str(state.root) if state.root else None,
        }

    def list_vaults(self) -> List[Dict]:
        return [self.vault_metadata(vault_id) for vault_id in sorted(self._vaults)]

    @property
    def selected_vault_id(self) -> str:
        return self._selected_vault_id

    def select_vault(self, vault_id: str) -> Dict:
        if vault_id not in self._vaults:
            raise KeyError(vault_id)
        self._selected_vault_id = vault_id
        return {"selected": vault_id, "vault": self.vault_metadata(vault_id)}

    def index_vault(
        self, path: str, *, vault_id: str = "default", incremental: bool = False
    ) -> Dict:
        """Parse, embed, persist, and graph every note under ``path``."""
        state = self._state(vault_id)
        raw_path = Path(path)
        _reject_symlink_components(raw_path, label="vault root")
        resolved = raw_path.resolve(strict=False)
        if vault_id == "default":
            state.root = resolved
        elif state.root is None:
            state.root = resolved
        elif resolved != state.root:
            raise ValueError("path is outside vault root")
        self.events.publish(
            "index_started", vault_id=vault_id, data={"incremental": incremental}
        )
        try:
            notes = self.indexer.parse_directory(str(resolved))
            changes = self._changes(state, notes)
            if incremental and state.snapshots:
                existing = {
                    note["id"]: note
                    for note in state.note_store.list_notes(vault_id=vault_id)
                }
                changed_ids = set(changes["added"]) | set(changes["changed"])
                notes = [
                    existing.get(note["id"], note)
                    if note["id"] not in changed_ids
                    else note
                    for note in notes
                ]
            result = self._load(notes, path=path, vault_id=vault_id)
            if incremental:
                result["changes"] = changes
            self.events.publish(
                "index_completed",
                vault_id=vault_id,
                data={
                    "total_notes": result["total_notes"],
                    **({"changes": changes} if incremental else {}),
                },
            )
            return result
        except Exception as exc:
            self.events.publish(
                "index_failed",
                vault_id=vault_id,
                data={"error": type(exc).__name__},
            )
            raise

    def index_notes(self, notes: List[Dict], *, vault_id: str = "default") -> Dict:
        """Index already-parsed note dicts (used by tests/workers)."""
        return self._load(notes, path=None, vault_id=vault_id)

    def _load(
        self, notes: List[Dict], *, path: Optional[str], vault_id: str = "default"
    ) -> Dict:
        state = self._state(vault_id)
        unembedded = [
            chunk
            for note in notes
            for chunk in note.get("chunks", [])
            if chunk.get("embedding") is None
        ]
        if unembedded:
            self.embedder.embed_chunks(unembedded)
        state.note_store.replace_all(notes, vault_id=vault_id)
        build_vector_store(notes, self.embedder, state.vector_store)
        state.graph.build_graph(notes)
        state.snapshots = {
            note["id"]: str(note.get("content_hash", "")) for note in notes
        }
        return {
            "indexed_path": path,
            "total_notes": len(notes),
            "total_chunks": sum(len(n.get("chunks", [])) for n in notes),
            "total_links": sum(len(n.get("links", [])) for n in notes),
            "total_tags": len(self.list_tags(vault_id=vault_id)),
        }

    @staticmethod
    def _changes(state: _VaultState, notes: List[Dict]) -> Dict[str, List[str]]:
        current = {note["id"]: str(note.get("content_hash", "")) for note in notes}
        previous = state.snapshots
        return {
            "added": sorted(set(current) - set(previous)),
            "changed": sorted(
                note_id
                for note_id in set(current) & set(previous)
                if current[note_id] != previous[note_id]
            ),
            "deleted": sorted(set(previous) - set(current)),
        }

    def reindex_from_store(self, *, vault_id: str = "default") -> None:
        """Rebuild the in-memory graph + vector store from persisted notes.

        Called on startup when notes were loaded from the database in a prior run
        so search and the graph work immediately without re-parsing the vault.
        """
        state = self._state(vault_id)
        notes = state.note_store.list_notes(vault_id=vault_id)
        if not notes:
            return
        for note in notes:
            if not note.get("chunks"):
                continue
            if note["chunks"][0].get("embedding") is None:
                self.embedder.embed_chunks(note["chunks"])
        build_vector_store(notes, self.embedder, state.vector_store)
        state.graph.build_graph(notes)
        state.snapshots = {
            note["id"]: str(note.get("content_hash", "")) for note in notes
        }

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #
    def search(
        self,
        query: str,
        limit: int = 5,
        *,
        mode: str = "keyword",
        vault_id: str = "default",
        tags: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Search notes by ``keyword`` (default), ``semantic``, or ``hybrid``."""
        state = self._state(vault_id)
        notes = state.note_store.list_notes(vault_id=vault_id)
        if tags:
            selected = {tag.lower().lstrip("#") for tag in tags}
            notes = [
                note
                for note in notes
                if selected <= {tag.lower().lstrip("#") for tag in note.get("tags", [])}
            ]
        if mode == "semantic":
            return semantic_search(
                notes, query, limit, embedder=self.embedder, store=state.vector_store
            )
        if mode == "hybrid":
            return self._hybrid(notes, query, limit, vector_store=state.vector_store)
        return keyword_search(notes, query, limit)

    def _hybrid(
        self,
        notes: List[Dict],
        query: str,
        limit: int,
        *,
        vector_store: Optional[VectorStore] = None,
    ) -> List[Dict]:
        """Merge keyword + semantic results, de-duplicated by note id."""
        merged: Dict[str, Dict] = {}
        for result in keyword_search(notes, query, limit):
            merged[result["id"]] = result
        for result in semantic_search(
            notes,
            query,
            limit,
            embedder=self.embedder,
            store=vector_store or self.vector_store,
        ):
            if result["id"] not in merged:
                merged[result["id"]] = result
        ranked = sorted(merged.values(), key=lambda r: r["score"], reverse=True)
        return ranked[:limit]

    def chat(self, query: str, *, limit: int = 3, vault_id: str = "default") -> Dict:
        """Retrieve top notes (semantic) and answer with cited grounding."""
        state = self._state(vault_id)
        notes = state.note_store.list_notes(vault_id=vault_id)
        retrieved = semantic_search(
            notes, query, limit, embedder=self.embedder, store=state.vector_store
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
    def get_note(self, note_id: str, *, vault_id: str = "default") -> Optional[Dict]:
        note = self._state(vault_id).note_store.get_note(note_id, vault_id=vault_id)
        if note is None:
            return None
        public = dict(note)
        if vault_id == "default":
            public.pop("vault_id", None)
        return public

    def get_backlinks(self, note_id: str, *, vault_id: str = "default") -> List[str]:
        return self._state(vault_id).graph.get_backlinks(note_id)

    def get_graph(self, *, vault_id: str = "default") -> Dict:
        return self._state(vault_id).graph.get_graph()

    def list_tags(self, *, vault_id: str = "default") -> List[Dict]:
        """Return tag -> note-count rollup across all indexed notes."""
        counts: Dict[str, int] = {}
        notes_by_tag: Dict[str, List[str]] = {}
        for note in self._state(vault_id).note_store.list_notes(vault_id=vault_id):
            for tag in note.get("tags", []):
                counts[tag] = counts.get(tag, 0) + 1
                notes_by_tag.setdefault(tag, []).append(note["id"])
        return [
            {"tag": tag, "count": counts[tag], "notes": notes_by_tag[tag]}
            for tag in sorted(counts)
        ]

    def stats(self, *, vault_id: str = "default") -> Dict:
        state = self._state(vault_id)
        notes = state.note_store.list_notes(vault_id=vault_id)
        return {
            "total_notes": len(notes),
            "total_chunks": state.vector_store.count(),
            "total_tags": len(self.list_tags(vault_id=vault_id)),
        }

    def update_note(
        self, note_id: str, content: str, *, vault_id: str = "default"
    ) -> Dict:
        if "\x00" in content:
            raise ValueError("note content must be text")
        if len(content.encode("utf-8")) > 2 * 1024 * 1024:
            raise ValueError("note content exceeds the 2 MiB limit")
        state = self._state(vault_id)
        note = state.note_store.get_note(note_id, vault_id=vault_id)
        if note is None:
            raise KeyError(note_id)
        if state.root is None or not note.get("source"):
            raise ValueError("note has no editable vault source")
        _reject_symlink_components(state.root, label="vault root")
        root = state.root.resolve(strict=True)
        unresolved_target = root / str(note["source"])
        _reject_symlink_components(unresolved_target, label="note path")
        target = unresolved_target.resolve(strict=False)
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("note path is outside vault root") from exc
        target.write_text(content, encoding="utf-8")
        parsed = self.indexer.parse_note(content, source=str(note["source"]))
        # Preserve the route id even if a caller edited the source metadata elsewhere.
        parsed["id"] = note_id
        self.index_vault(str(root), vault_id=vault_id, incremental=True)
        updated = state.note_store.get_note(note_id, vault_id=vault_id)
        self.events.publish(
            "note_changed",
            vault_id=vault_id,
            data={"note_id": note_id, "content_hash": parsed["content_hash"]},
        )
        return updated or parsed

    def save_search(
        self,
        *,
        name: str,
        query: str,
        mode: str = "keyword",
        tags: Optional[List[str]] = None,
        vault_id: str = "default",
    ) -> Dict:
        if mode not in {"keyword", "semantic", "hybrid"}:
            raise ValueError("invalid search mode")
        normalized_tags = sorted({tag.lower().lstrip("#") for tag in tags or []})
        seed = f"{vault_id}\0{name}\0{query}\0{mode}\0{','.join(normalized_tags)}"
        search_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        saved = {
            "id": search_id,
            "vault_id": vault_id,
            "name": name,
            "query": query,
            "mode": mode,
            "tags": normalized_tags,
        }
        self._saved_searches[(vault_id, search_id)] = saved
        return dict(saved)

    def list_saved_searches(self, *, vault_id: str = "default") -> List[Dict]:
        return [
            dict(value)
            for (scope, _), value in sorted(self._saved_searches.items())
            if scope == vault_id
        ]

    def delete_saved_search(self, search_id: str, *, vault_id: str = "default") -> bool:
        return self._saved_searches.pop((vault_id, search_id), None) is not None

    def generate_flashcards(
        self,
        *,
        vault_id: str = "default",
        note_id: Optional[str] = None,
        enrich: bool = False,
    ) -> List[Dict]:
        notes = self._state(vault_id).note_store.list_notes(vault_id=vault_id)
        if note_id:
            notes = [note for note in notes if note.get("id") == note_id]
        return self.flashcards.generate(notes, vault_id=vault_id, enrich=enrich)

    def start_watcher(self, vault_id: str = "default") -> Dict:
        state = self._state(vault_id)
        if state.root is None:
            raise ValueError("vault has no configured path")
        watcher = self._watchers.get(vault_id)
        if watcher is None:

            def reindex_changed_vault() -> None:
                self.index_vault(str(state.root), vault_id=vault_id, incremental=True)

            watcher = PollingVaultWatcher(
                vault_id=vault_id,
                root=state.root,
                event_bus=self.events,
                on_change=reindex_changed_vault,
            )
            self._watchers[vault_id] = watcher
        watcher.start()
        return self.watcher_status(vault_id)

    def stop_watcher(self, vault_id: str = "default") -> Dict:
        watcher = self._watchers.get(vault_id)
        if watcher:
            watcher.stop()
        return self.watcher_status(vault_id)

    def watcher_status(self, vault_id: str = "default") -> Dict:
        watcher = self._watchers.get(vault_id)
        return {
            "vault_id": vault_id,
            "running": bool(watcher and watcher.running),
            "backend": "polling",
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
