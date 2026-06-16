"""Worker tests: pure task logic runs without a broker."""

from apps.api.src import worker


class TestWorker:
    def test_celery_app_importable_without_broker(self):
        assert worker.celery_app is not None
        assert worker.celery_app.main == worker.config.APP_NAME

    def test_index_vault_task_registered(self):
        assert "kb.index_vault" in worker.celery_app.tasks
        assert "kb.reindex" in worker.celery_app.tasks

    def test_index_vault_pure_logic(self, vault_path):
        # Offline: check_db falls back to in-memory, indexing still works.
        summary = worker._index_vault(vault_path)
        assert summary["total_notes"] >= 8

    def test_index_empty_vault(self):
        summary = worker._index_vault("/no/such/path")
        assert summary["total_notes"] == 0
