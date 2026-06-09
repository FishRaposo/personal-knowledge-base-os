from typing import Dict, List


def chat_with_citations(
    query: str,
    retrieved_notes: List[Dict],
) -> Dict:
    if not retrieved_notes:
        return {
            "answer": "I don't have any notes that address your question.",
            "citations": [],
        }

    combined = " ".join([n.get("content", "") for n in retrieved_notes])
    answer = f"Based on your notes: {combined[:200]}..."

    citations = []
    for note in retrieved_notes:
        title = note.get("title", "untitled")
        snippet = note.get("content", "")[:60]
        citations.append({"title": title, "snippet": snippet})

    return {"answer": answer, "citations": citations}
