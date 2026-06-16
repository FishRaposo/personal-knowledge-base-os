"""Embedding generation for the knowledge base.

Wraps ``shared_core.embeddings`` so the same code path runs offline (a
deterministic ``HashFallbackProvider`` — no API key, no network, no torch) and
real-when-keyed (the OpenAI provider when ``OPENAI_API_KEY`` is configured). The
synchronous wrappers here let the (sync) FastAPI endpoints and the indexer embed
text without each call site juggling an event loop.
"""

import asyncio
from typing import Any, Dict, List, Optional

from shared_core.embeddings import (
    EmbeddingProvider,
    cosine_similarity,
    get_embedding_provider,
)


class EmbeddingGenerator:
    """Synchronous facade over a ``shared_core`` embedding provider.

    Offline-first: defaults to the deterministic hash-fallback provider so tests
    and the demo run with no API key. Pass ``offline=False`` with an ``api_key``
    to use the real OpenAI embeddings endpoint.
    """

    def __init__(
        self,
        *,
        provider: Optional[EmbeddingProvider] = None,
        offline: bool = True,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
    ) -> None:
        self.provider = provider or get_embedding_provider(
            api_key=api_key, model=model, offline=offline
        )

    @property
    def dimensions(self) -> int:
        """Vector dimensionality of the active provider (default 384 offline)."""
        return getattr(self.provider, "dimensions", 384)

    def embed_text(self, text: str) -> List[float]:
        """Return the embedding vector for a single string."""
        result = _run(self.provider.embed(text or ""))
        return result.vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Return embedding vectors for a list of strings."""
        results = _run(self.provider.embed_batch([t or "" for t in texts]))
        return [r.vector for r in results]

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Attach an ``embedding`` to each chunk dict (by its ``content``)."""
        texts = [chunk.get("content", "") for chunk in chunks]
        vectors = self.embed_batch(texts)
        for chunk, vector in zip(chunks, vectors, strict=False):
            chunk["embedding"] = vector
        return chunks


def _run(coro: Any) -> Any:
    """Run an awaitable from sync code, even when no loop is running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # A loop is already running (rare in our sync endpoints) — use a fresh loop.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


__all__ = ["EmbeddingGenerator", "cosine_similarity"]
