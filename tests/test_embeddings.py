"""Embedding generator tests (offline hash-fallback, deterministic)."""

from apps.api.src.embeddings import EmbeddingGenerator, cosine_similarity


class TestEmbeddingGenerator:
    def test_embed_text_returns_vector(self):
        gen = EmbeddingGenerator(offline=True)
        vec = gen.embed_text("hello world")
        assert isinstance(vec, list)
        assert len(vec) == gen.dimensions
        assert all(isinstance(x, float) for x in vec)

    def test_deterministic(self):
        gen = EmbeddingGenerator(offline=True)
        assert gen.embed_text("same text") == gen.embed_text("same text")

    def test_different_text_different_vector(self):
        gen = EmbeddingGenerator(offline=True)
        assert gen.embed_text("alpha") != gen.embed_text("beta")

    def test_embed_batch(self):
        gen = EmbeddingGenerator(offline=True)
        vectors = gen.embed_batch(["a", "b", "c"])
        assert len(vectors) == 3
        assert all(len(v) == gen.dimensions for v in vectors)

    def test_embed_chunks_attaches_embedding(self):
        gen = EmbeddingGenerator(offline=True)
        chunks = [{"content": "one"}, {"content": "two"}]
        out = gen.embed_chunks(chunks)
        assert all("embedding" in c for c in out)
        assert len(out[0]["embedding"]) == gen.dimensions

    def test_empty_text_is_safe(self):
        gen = EmbeddingGenerator(offline=True)
        vec = gen.embed_text("")
        assert len(vec) == gen.dimensions

    def test_self_similarity_is_high(self):
        gen = EmbeddingGenerator(offline=True)
        vec = gen.embed_text("knowledge base")
        assert cosine_similarity(vec, vec) > 0.99
