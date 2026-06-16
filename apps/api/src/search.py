"""Keyword and semantic search over indexed notes.

``keyword_search`` is a transparent, explainable lexical scorer (exact/partial
title, content frequency, tag hits). ``semantic_search`` runs real vector
retrieval over ``shared_core.vectorstore`` (``InMemoryVectorStore`` offline,
``PgVectorStore`` when a database is configured) using the chunk embeddings the
indexer produced — chunk hits are rolled up to their parent note, keeping the
best-scoring chunk as the matched snippet.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from shared_core.vectorstore import VectorRecord, VectorStore

from .embeddings import EmbeddingGenerator


class Note(BaseModel):
    """Public note schema (also used to validate persisted payloads)."""

    id: str
    title: str
    content: str
    links: list[str] = []
    tags: list[str] = []


def keyword_search(notes: List[Dict], query: str, limit: int = 5) -> List[Dict]:
    """Score notes by lexical overlap and return the top ``limit`` ranked notes."""
    query_lower = query.lower().strip()
    if not query_lower:
        return []
    query_words = [w for w in query_lower.split() if w]
    scored: list[tuple[float, dict]] = []

    for note in notes:
        title_lower = note.get("title", "").lower()
        content_lower = note.get("content", "").lower()
        tags_lower = [t.lower() for t in note.get("tags", [])]
        score = 0.0

        if query_lower == title_lower:
            score += 100
        elif query_lower in title_lower:
            score += 50

        score += content_lower.count(query_lower) * 2

        for word in query_words:
            if word in title_lower:
                score += 5
            if word in tags_lower:
                score += 8
            score += content_lower.count(word)

        if score > 0:
            scored.append((score, _result(note, score=score, match="keyword")))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def build_vector_store(
    notes: List[Dict],
    embedder: EmbeddingGenerator,
    store: VectorStore,
) -> VectorStore:
    """Embed each note's chunks and load them into ``store``. Returns the store."""
    store.clear()
    for note in notes:
        chunks = note.get("chunks") or [
            {
                "id": f"{note.get('id', note.get('title', ''))}::0",
                "note_id": note.get("id", note.get("title", "")),
                "index": 0,
                "content": note.get("content", ""),
            }
        ]
        for chunk in chunks:
            vector = chunk.get("embedding") or embedder.embed_text(
                chunk.get("content", "")
            )
            store.add(
                VectorRecord(
                    id=chunk["id"],
                    vector=vector,
                    payload={
                        "note_id": chunk.get("note_id", note.get("id")),
                        "title": note.get("title", ""),
                        "snippet": chunk.get("content", "")[:280],
                        "index": chunk.get("index", 0),
                    },
                )
            )
    return store


def semantic_search(
    notes: List[Dict],
    query: str,
    limit: int = 5,
    *,
    embedder: Optional[EmbeddingGenerator] = None,
    store: Optional[VectorStore] = None,
) -> List[Dict]:
    """Vector-search ``query`` over note chunks; roll chunk hits up to notes.

    When a prebuilt ``store`` is supplied (the API path), it is queried directly.
    Otherwise an in-memory store is built on the fly from ``notes`` so the helper
    is usable standalone in tests.
    """
    if not query.strip() or not notes:
        return []
    embedder = embedder or EmbeddingGenerator(offline=True)

    if store is None:
        from shared_core.vectorstore import InMemoryVectorStore

        store = build_vector_store(notes, embedder, InMemoryVectorStore())

    query_vector = embedder.embed_text(query)
    # Over-fetch chunks so several can collapse into the same note.
    hits = store.query(query_vector, top_k=max(limit * 4, limit))

    notes_by_id: Dict[str, Dict] = {
        str(note.get("id") or note.get("title") or ""): note for note in notes
    }
    best: Dict[str, Dict[str, Any]] = {}
    for hit in hits:
        note_id = hit.payload.get("note_id")
        if not note_id or note_id not in notes_by_id:
            continue
        if note_id not in best or hit.score > best[note_id]["score"]:
            best[note_id] = {"score": hit.score, "snippet": hit.payload.get("snippet")}

    ranked = sorted(best.items(), key=lambda item: item[1]["score"], reverse=True)
    results: List[Dict] = []
    for note_id, info in ranked[:limit]:
        note = notes_by_id[note_id]
        results.append(
            _result(
                note,
                score=round(float(info["score"]), 4),
                match="semantic",
                snippet=info["snippet"],
            )
        )
    return results


def _result(
    note: Dict,
    *,
    score: float,
    match: str,
    snippet: Optional[str] = None,
) -> Dict:
    """Normalize a note into a search-result dict."""
    return {
        "id": note.get("id", note.get("title", "")),
        "title": note.get("title", ""),
        "snippet": snippet if snippet is not None else note.get("content", "")[:280],
        "content": note.get("content", ""),
        "tags": note.get("tags", []),
        "links": note.get("links", []),
        "score": score,
        "match_type": match,
    }
