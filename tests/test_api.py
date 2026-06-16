"""API endpoint tests — every endpoint, success + error paths.

The app boots fully offline (in-memory stores, offline embeddings, simulated
chat). ``db_manager`` / ``redis_manager`` are patched so ``/health`` is fast and
deterministic (the real check_health does live socket connects). A plain
``TestClient`` is used (not as a context manager) so the DB-probe lifespan does
not run and the service stays offline-in-memory.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from apps.api.src import main
    from apps.api.src.engine import KnowledgeBase

    # Fresh offline state per test for isolation.
    main.kb = KnowledgeBase(config=main.config)
    main.indexer = main.kb.indexer
    main.graph = main.kb.graph

    mock_db = MagicMock()
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    with (
        patch.object(main, "db_manager", mock_db),
        patch.object(main, "redis_manager", mock_redis),
    ):
        yield TestClient(main.app)


@pytest.fixture
def indexed_client(client):
    resp = client.post("/notes/index", json={})
    assert resp.status_code == 200
    return client


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["service"] == "personal-knowledge-base-os"
        assert "dependencies" in body


class TestIndexEndpoint:
    def test_index_default_vault(self, client):
        resp = client.post("/notes/index", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_notes"] >= 8
        assert "graph" in body
        assert body["graph"]["nodes"]

    def test_index_get_wrapper(self, client):
        resp = client.get("/notes/index")
        assert resp.status_code == 200
        assert resp.json()["total_notes"] >= 8

    def test_index_missing_path_errors(self, client):
        resp = client.post("/notes/index", json={"path": "/no/such/vault"})
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"


class TestSearchEndpoint:
    def test_keyword_search(self, indexed_client):
        resp = indexed_client.get("/notes/search", params={"q": "wikilinks"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "keyword"
        assert body["total"] >= 1

    def test_semantic_search(self, indexed_client):
        resp = indexed_client.get(
            "/notes/search", params={"q": "related ideas", "mode": "semantic"}
        )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "semantic"

    def test_hybrid_search(self, indexed_client):
        resp = indexed_client.get(
            "/notes/search", params={"q": "embeddings", "mode": "hybrid"}
        )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "hybrid"

    def test_invalid_mode_rejected(self, indexed_client):
        resp = indexed_client.get("/notes/search", params={"q": "x", "mode": "bogus"})
        assert resp.status_code == 422

    def test_missing_query_rejected(self, indexed_client):
        resp = indexed_client.get("/notes/search")
        assert resp.status_code == 422


class TestChatEndpoint:
    def test_chat_returns_grounded_answer(self, indexed_client):
        resp = indexed_client.post(
            "/notes/chat", json={"query": "How does the graph work?"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["citations"]
        assert body["grounded"] is True
        assert "[1]" in body["answer"]

    def test_chat_requires_query(self, indexed_client):
        resp = indexed_client.post("/notes/chat", json={})
        assert resp.status_code == 422


class TestNoteBrowsing:
    def test_get_note(self, indexed_client):
        resp = indexed_client.get("/notes/getting_started")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Getting Started"
        assert "backlinks" in body

    def test_get_note_not_found(self, indexed_client):
        resp = indexed_client.get("/notes/does_not_exist")
        assert resp.status_code == 404
        assert resp.json()["error"] == "NOT_FOUND"

    def test_backlinks(self, indexed_client):
        resp = indexed_client.get("/notes/notes_architecture/backlinks")
        assert resp.status_code == 200
        body = resp.json()
        assert body["note_id"] == "notes_architecture"
        assert "getting_started" in body["backlinks"]


class TestGraphAndTags:
    def test_graph(self, indexed_client):
        resp = indexed_client.get("/graph")
        assert resp.status_code == 200
        body = resp.json()
        assert body["nodes"]
        assert body["edges"]

    def test_tags(self, indexed_client):
        resp = indexed_client.get("/tags")
        assert resp.status_code == 200
        tags = resp.json()["tags"]
        assert tags
        assert {"tag", "count", "notes"} <= set(tags[0])

    def test_stats(self, indexed_client):
        resp = indexed_client.get("/stats")
        assert resp.status_code == 200
        assert resp.json()["total_notes"] >= 8
