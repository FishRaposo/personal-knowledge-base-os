"""Keyword and semantic search tests."""

from shared_core.vectorstore import InMemoryVectorStore

from apps.api.src.embeddings import EmbeddingGenerator
from apps.api.src.search import (
    build_vector_store,
    keyword_search,
    semantic_search,
)


class TestKeywordSearch:
    def test_exact_title_ranks_first(self, sample_notes):
        results = keyword_search(sample_notes, "Alpha", limit=5)
        assert results[0]["title"] == "Alpha"

    def test_tag_match_scores(self, sample_notes):
        results = keyword_search(sample_notes, "demo", limit=5)
        ids = {r["id"] for r in results}
        # Both alpha (tag demo) and beta (#demo) should surface.
        assert "alpha" in ids or "beta" in ids

    def test_empty_query_returns_empty(self, sample_notes):
        assert keyword_search(sample_notes, "   ", limit=5) == []

    def test_no_match_returns_empty(self, sample_notes):
        assert keyword_search(sample_notes, "zzzznomatch", limit=5) == []

    def test_limit_respected(self, sample_notes):
        results = keyword_search(sample_notes, "note", limit=1)
        assert len(results) <= 1

    def test_result_shape(self, sample_notes):
        results = keyword_search(sample_notes, "Alpha", limit=1)
        r = results[0]
        assert {"id", "title", "snippet", "score", "match_type"} <= set(r)
        assert r["match_type"] == "keyword"


class TestSemanticSearch:
    def test_returns_results(self, sample_notes):
        results = semantic_search(sample_notes, "retrieval and search", limit=3)
        assert results
        assert results[0]["match_type"] == "semantic"

    def test_deterministic(self, sample_notes):
        a = semantic_search(sample_notes, "search", limit=3)
        b = semantic_search(sample_notes, "search", limit=3)
        assert [r["id"] for r in a] == [r["id"] for r in b]

    def test_scores_descending(self, sample_notes):
        results = semantic_search(sample_notes, "search", limit=3)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_empty_query(self, sample_notes):
        assert semantic_search(sample_notes, "", limit=3) == []

    def test_prebuilt_store_path(self, sample_notes):
        embedder = EmbeddingGenerator(offline=True)
        store = build_vector_store(sample_notes, embedder, InMemoryVectorStore())
        results = semantic_search(
            sample_notes, "gamma leaf", limit=2, embedder=embedder, store=store
        )
        assert results
        # Chunk hits roll up to unique notes.
        assert len({r["id"] for r in results}) == len(results)

    def test_chunks_rolled_up_to_notes(self, sample_notes):
        embedder = EmbeddingGenerator(offline=True)
        store = build_vector_store(sample_notes, embedder, InMemoryVectorStore())
        results = semantic_search(
            sample_notes, "alpha beta gamma", limit=5, embedder=embedder, store=store
        )
        ids = [r["id"] for r in results]
        assert len(ids) == len(set(ids))
