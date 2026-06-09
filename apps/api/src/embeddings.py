from typing import Any, Dict, List


class MockEmbeddingGenerator:
    """Generates mock embedding vectors for testing."""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        val = sum(ord(c) for c in text[:100]) / 1000.0
        return [val * (i + 1) / self.dimension for i in range(self.dimension)]

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for chunk in chunks:
            chunk["embedding"] = self.embed_text(chunk.get("content", ""))
        return chunks
