from typing import Dict, List

from pydantic import BaseModel


class Note(BaseModel):
    title: str
    content: str
    links: list[str]


def keyword_search(notes: List[Dict], query: str, limit: int = 5) -> List[Dict]:
    query_lower = query.lower()
    scored: list[tuple[int, dict]] = []

    for note in notes:
        score = 0
        title_lower = note.get("title", "").lower()
        content_lower = note.get("content", "").lower()

        if query_lower == title_lower:
            score += 100
        elif query_lower in title_lower:
            score += 50

        score += content_lower.count(query_lower) * 2

        query_words = query_lower.split()
        for word in query_words:
            if word in title_lower:
                score += 5
            score += content_lower.count(word)

        if score > 0:
            scored.append((score, note))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def semantic_search(
    notes: List[Dict], query: str, limit: int = 5
) -> List[Dict]:
    """Placeholder semantic search using keyword overlap as proxy."""
    return keyword_search(notes, query, limit)
