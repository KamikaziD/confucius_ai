from celery import Celery
from app.config import settings

celery_app = Celery(
    "multi_agent_system",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)

# Import tasks here to ensure they are registered
from app.tasks import execute_master_agent_task
