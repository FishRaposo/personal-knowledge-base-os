from unittest.mock import MagicMock, patch


def test_health_endpoint():
    mock_db = MagicMock()
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with (
        patch("apps.api.src.main.db_manager", mock_db),
        patch("apps.api.src.main.redis_manager", mock_redis),
        patch("apps.api.src.main.indexer", MagicMock()),
        patch("apps.api.src.main.graph", MagicMock()),
    ):
        from fastapi.testclient import TestClient

        from apps.api.src.main import app

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert "status" in response.json()


def test_notes_index_endpoint():
    mock_db = MagicMock()
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_indexer = MagicMock()
    mock_indexer.parse_directory.return_value = [
        {"title": "Test", "links": ["Link1"]}
    ]
    mock_graph = MagicMock()
    mock_graph.build_graph.return_value = None
    mock_graph.adj_list = {"Test": {"Link1"}}

    with (
        patch("apps.api.src.main.db_manager", mock_db),
        patch("apps.api.src.main.redis_manager", mock_redis),
        patch("apps.api.src.main.indexer", mock_indexer),
        patch("apps.api.src.main.graph", mock_graph),
    ):
        from fastapi.testclient import TestClient

        from apps.api.src.main import app

        with TestClient(app) as client:
            response = client.get("/notes/index?path=docs")
            assert response.status_code == 200
            assert "total_notes" in response.json()
