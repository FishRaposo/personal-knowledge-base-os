"""KnowledgeBase engine integration tests (end-to-end, offline)."""

from apps.api.src.engine import KnowledgeBase


class TestKnowledgeBaseIndexing:
    def test_index_vault_summary(self, vault_path):
        kb = KnowledgeBase()
        summary = kb.index_vault(vault_path)
        assert summary["total_notes"] >= 8
        assert summary["total_chunks"] >= summary["total_notes"]
        assert summary["total_links"] > 0
        assert summary["total_tags"] > 0

    def test_index_empty_path(self):
        kb = KnowledgeBase()
        summary = kb.index_vault("/no/such/vault/path")
        assert summary["total_notes"] == 0

    def test_index_notes_directly(self, sample_notes):
        kb = KnowledgeBase()
        summary = kb.index_notes(sample_notes)
        assert summary["total_notes"] == 3


class TestKnowledgeBaseRetrieval:
    def test_keyword_search(self, indexed_kb):
        results = indexed_kb.search("wikilinks", limit=3, mode="keyword")
        assert results
        assert results[0]["match_type"] == "keyword"

    def test_semantic_search(self, indexed_kb):
        results = indexed_kb.search("find related ideas", limit=3, mode="semantic")
        assert results
        assert results[0]["match_type"] == "semantic"

    def test_hybrid_search(self, indexed_kb):
        results = indexed_kb.search("embeddings", limit=5, mode="hybrid")
        assert results
        ids = [r["id"] for r in results]
        assert len(ids) == len(set(ids))  # de-duplicated

    def test_chat_grounded(self, indexed_kb):
        result = indexed_kb.chat("How does the backlinks graph work?", limit=3)
        assert result["citations"]
        assert result["grounded"] is True


class TestKnowledgeBaseGraph:
    def test_backlinks(self, indexed_kb):
        backlinks = indexed_kb.get_backlinks("notes_architecture")
        assert "getting_started" in backlinks

    def test_graph_export(self, indexed_kb):
        graph = indexed_kb.get_graph()
        assert len(graph["nodes"]) >= 8
        assert graph["edges"]

    def test_get_note(self, indexed_kb):
        note = indexed_kb.get_note("getting_started")
        assert note is not None
        assert note["title"] == "Getting Started"

    def test_tags(self, indexed_kb):
        tags = indexed_kb.list_tags()
        assert tags
        names = {t["tag"] for t in tags}
        assert "architecture" in names

    def test_stats(self, indexed_kb):
        stats = indexed_kb.stats()
        assert stats["total_notes"] >= 8
        assert stats["total_chunks"] > 0


class TestReindexFromStore:
    def test_reindex_rebuilds_graph(self, sample_notes):
        kb = KnowledgeBase()
        kb.note_store.replace_all(sample_notes)
        kb.reindex_from_store()
        # Graph and vector store should be populated from the persisted notes.
        assert kb.get_graph()["nodes"]
        assert kb.search("gamma", mode="semantic")
