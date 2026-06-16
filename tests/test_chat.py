"""Chat-with-citations tests (offline simulated path + citation grounding)."""

from apps.api.src.chat import chat_with_citations


def _retrieved():
    return [
        {
            "id": "a",
            "title": "Alpha",
            "snippet": "Alpha explains the backlinks graph.",
            "score": 0.9,
        },
        {
            "id": "b",
            "title": "Beta",
            "snippet": "Beta covers semantic search.",
            "score": 0.7,
        },
    ]


class TestChatWithCitations:
    def test_refusal_when_no_notes(self):
        result = chat_with_citations("anything", [])
        assert result["citations"] == []
        assert result["grounded"] is False
        assert result["mode"] == "refusal"

    def test_simulated_answer_is_grounded(self):
        result = chat_with_citations("how does the graph work?", _retrieved())
        assert result["mode"] == "simulated"
        assert result["grounded"] is True
        assert result["citation_score"] == 1.0

    def test_answer_contains_citation_markers(self):
        result = chat_with_citations("question", _retrieved())
        assert "[1]" in result["answer"]
        assert "[2]" in result["answer"]

    def test_citations_indexed_from_one(self):
        result = chat_with_citations("q", _retrieved())
        indices = [c["index"] for c in result["citations"]]
        assert indices == [1, 2]

    def test_citation_titles_preserved(self):
        result = chat_with_citations("q", _retrieved())
        titles = [c["title"] for c in result["citations"]]
        assert titles == ["Alpha", "Beta"]

    def test_no_keys_uses_simulated_model(self):
        result = chat_with_citations("q", _retrieved(), api_keys={})
        assert result["model"] == "simulated"

    def test_falls_back_when_key_present_but_sdk_missing(self):
        # A fake key is set but the openai SDK is not installed in the test env,
        # so the real path raises ImportError and we fall back to simulation.
        result = chat_with_citations("q", _retrieved(), api_keys={"openai": "sk-fake"})
        assert result["grounded"] is True
        assert result["model"] == "simulated"
