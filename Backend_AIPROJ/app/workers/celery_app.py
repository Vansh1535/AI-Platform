"""
Celery application configuration for background task processing.
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "enterprise_project",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    result_expires=3600,  # 1 hour
)

# Auto-discover tasks from workers.tasks module
celery_app.autodiscover_tasks(["app.workers"])
