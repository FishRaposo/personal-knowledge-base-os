from typing import Any

from loguru import logger


class _LocalTask:
    """Synchronous task facade used when Celery is not installed."""

    def __init__(self, function: Any, name: str) -> None:
        self.function = function
        self.name = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.function(*args, **kwargs)

    def delay(self, *args: Any, **kwargs: Any) -> Any:
        """Execute immediately in the offline compatibility path."""
        return self.function(*args, **kwargs)


class _LocalCelery:
    """Minimal broker-free registry matching the subset used by this API."""

    def __init__(self, service_name: str) -> None:
        self.main = service_name
        self.tasks: dict[str, _LocalTask] = {}

    def task(self, *, name: str):
        def register(function: Any) -> _LocalTask:
            task = _LocalTask(function, name)
            self.tasks[name] = task
            return task

        return register


def create_celery_app(
    service_name: str,
    broker_url: str = "redis://localhost:6379/0",
    backend_url: str = "redis://localhost:6379/0",
) -> Any:
    """Dynamically bootstraps a Celery application with unified logging and settings."""
    try:
        from celery import Celery  # type: ignore
    except ImportError:
        return _LocalCelery(service_name)

    app = Celery(
        service_name,
        broker=broker_url,
        backend=backend_url,
    )

    # Apply configuration defaults
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,
    )

    from celery.signals import task_failure, task_postrun, task_prerun  # type: ignore

    @task_prerun.connect
    def on_task_prerun(task_id: str, task: Any, *args: Any, **kwargs: Any) -> None:
        logger.info(f"Celery task started: {task.name}[{task_id}]")

    @task_postrun.connect
    def on_task_postrun(
        task_id: str,
        task: Any,
        retval: Any,
        state: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        logger.info(f"Celery task completed: {task.name}[{task_id}] - State: {state}")

    @task_failure.connect
    def on_task_failure(
        task_id: str,
        exception: Exception,
        traceback: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        logger.error(
            f"Celery task failed: task_id={task_id} - Exception: {str(exception)}"
        )

    return app
