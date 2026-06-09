from celery import Celery
from shared_core.config import BaseAppConfig

config = BaseAppConfig()
celery_app = Celery(
    config.APP_NAME,
    broker=config.REDIS_URL,
    backend=config.REDIS_URL
)

# Set Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task
def sample_background_task(x: int, y: int) -> int:
    """A template background task."""
    return x + y
