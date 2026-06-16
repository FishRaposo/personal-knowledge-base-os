"""Golden / regression tests for the AI logic.

Locks in (a) the deterministic offline embedding output, (b) the
``shared_core.evaljudge.CitationJudge`` scoring used by chat, and (c) the
deterministic semantic-search ranking over the demo vault. If a scorer or
embedding path is swapped, these golden values catch silent drift.
"""

from apps.api.src.chat import chat_with_citations
from apps.api.src.embeddings import EmbeddingGenerator


class TestEmbeddingGolden:
    def test_known_vector_prefix(self):
        # The offline hash-fallback is deterministic; pin the first components so
        # an accidental provider/dimension change is caught.
        vec = EmbeddingGenerator(offline=True).embed_text("knowledge")
        assert len(vec) == 384
        prefix = [round(x, 4) for x in vec[:3]]
        assert prefix == _GOLDEN_KNOWLEDGE_PREFIX, f"embedding drift: got {prefix}"


class TestCitationJudgeGolden:
    def test_grounded_answer_scores_one(self):
        retrieved = [
            {"id": "a", "title": "A", "snippet": "alpha", "score": 1.0},
            {"id": "b", "title": "B", "snippet": "beta", "score": 0.5},
        ]
        result = chat_with_citations("q", retrieved)
        # Two distinct [n] markers -> CitationJudge passes with score 1.0.
        assert result["grounded"] is True
        assert result["citation_score"] == 1.0

    def test_refusal_scores_zero(self):
        result = chat_with_citations("q", [])
        assert result["grounded"] is False
        assert result["citation_score"] == 0.0


class TestSemanticRankingGolden:
    def test_demo_vault_ranking_is_stable(self, indexed_kb):
        # The deterministic offline embeddings produce a stable ranking for a
        # fixed query over the fixed demo vault.
        results = indexed_kb.search(
            "how do embeddings power semantic search?", limit=3, mode="semantic"
        )
        top_ids = [r["id"] for r in results]
        # The same query must always return the same ordering.
        again = indexed_kb.search(
            "how do embeddings power semantic search?", limit=3, mode="semantic"
        )
        # Determinism: identical query -> identical ranking (the regression lock).
        assert [r["id"] for r in again] == top_ids
        assert len(top_ids) == 3
        # Every hit is a real indexed note with a finite similarity score.
        for result in results:
            assert indexed_kb.get_note(result["id"]) is not None
            assert -1.0 <= result["score"] <= 1.0
        # The top hit is stable across the fixed vault (pinned golden id).
        assert top_ids[0] == "getting_started"


# Pinned golden value for the offline hash-fallback embedding of "knowledge".
_GOLDEN_KNOWLEDGE_PREFIX = [-0.0713, -0.0705, -0.0504]
