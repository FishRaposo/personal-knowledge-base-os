"""Chat-with-citations over retrieved notes (RAG).

Offline-first / real-when-keyed, mirroring ``llm-cost-latency-monitor``'s SDK: by
default a deterministic *simulated* answer is composed from the retrieved chunks
(no network, no key); when an OpenAI/Anthropic key is configured the real
provider is called via ``shared_core.llm.LLMClientFactory``, falling back to the
simulation if the SDK is missing or the call fails. Every answer carries inline
``[n]`` citation markers, and the citation grounding is *scored* with
``shared_core.evaljudge.CitationJudge`` so we can assert the answer is grounded.
"""

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger
from shared_core.evaljudge import CitationJudge

_REFUSAL = "I don't have any notes that address that question."


def _run(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _build_prompt(query: str, citations: List[Dict]) -> str:
    """Compose a grounded RAG prompt that instructs inline ``[n]`` citations."""
    context = "\n".join(
        f"[{c['index']}] {c['title']}: {c['snippet']}" for c in citations
    )
    return (
        "Answer the question using ONLY the notes below. Cite every claim with the "
        "matching [n] marker. If the notes do not contain the answer, say so.\n\n"
        f"Notes:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    )


def _simulated_answer(query: str, citations: List[Dict]) -> str:
    """Deterministic offline answer: stitched snippets with inline [n] markers."""
    parts: List[str] = [f"Based on your notes, here is what relates to '{query}':"]
    for c in citations:
        snippet = c["snippet"].strip().replace("\n", " ")
        if len(snippet) > 160:
            snippet = snippet[:160].rstrip() + "…"
        parts.append(f"{snippet} [{c['index']}]")
    return " ".join(parts)


def _call_llm(prompt: str, *, model: str, api_keys: Dict[str, Optional[str]]) -> str:
    """Invoke the real LLM via shared_core. Raises on missing SDK / key."""
    from shared_core.llm import LLMClientFactory

    factory = LLMClientFactory(
        openai_api_key=api_keys.get("openai"),
        anthropic_api_key=api_keys.get("anthropic"),
    )
    is_anthropic = "claude" in model.lower()
    if is_anthropic and not api_keys.get("anthropic"):
        raise ImportError("No Anthropic API key configured")
    if not is_anthropic and not api_keys.get("openai"):
        raise ImportError("No OpenAI API key configured")

    if is_anthropic:
        response = _run(factory.generate_anthropic(model, prompt))
    else:
        response = _run(factory.generate_openai(model, prompt))
    return response.text


def chat_with_citations(
    query: str,
    retrieved_notes: List[Dict],
    *,
    model: str = "gpt-4o-mini",
    api_keys: Optional[Dict[str, Optional[str]]] = None,
    min_citations: int = 1,
) -> Dict:
    """Answer ``query`` from ``retrieved_notes`` with scored inline citations.

    Returns ``{answer, citations, grounded, citation_score, model, mode}``.
    """
    api_keys = api_keys or {}
    if not retrieved_notes:
        return {
            "answer": _REFUSAL,
            "citations": [],
            "grounded": False,
            "citation_score": 0.0,
            "model": "none",
            "mode": "refusal",
        }

    citations: List[Dict] = []
    for index, note in enumerate(retrieved_notes, start=1):
        snippet = note.get("snippet") or note.get("content", "")[:280]
        citations.append(
            {
                "index": index,
                "id": note.get("id", note.get("title", "")),
                "title": note.get("title", "untitled"),
                "snippet": snippet,
                "score": note.get("score"),
            }
        )

    has_key = bool(api_keys.get("openai") or api_keys.get("anthropic"))
    mode = "simulated"
    answer: str
    if has_key:
        prompt = _build_prompt(query, citations)
        try:
            answer = _call_llm(prompt, model=model, api_keys=api_keys)
            mode = "llm"
        except ImportError:
            logger.warning("LLM SDK/key unavailable — using simulated answer.")
            answer = _simulated_answer(query, citations)
            model = "simulated"
        except Exception as exc:  # noqa: BLE001 - never crash the request
            logger.error("LLM call failed ({}); using simulated answer.", exc)
            answer = _simulated_answer(query, citations)
            model = "simulated"
    else:
        answer = _simulated_answer(query, citations)
        model = "simulated"

    # Score citation grounding deterministically with the shared judge.
    judge = CitationJudge(min_citations=min_citations)
    verdict = _run(judge.evaluate(expected=None, actual=answer))

    return {
        "answer": answer,
        "citations": citations,
        "grounded": verdict.passed,
        "citation_score": verdict.score,
        "model": model,
        "mode": mode,
    }
