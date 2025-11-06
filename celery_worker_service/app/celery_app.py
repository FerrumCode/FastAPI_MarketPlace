from celery import Celery
from celery.schedules import crontab
from .config import settings
from .logging_conf import setup_logging

log = setup_logging()

celery_app = Celery(
    "julyberries_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    timezone="Europe/Bucharest",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    broker_connection_retry_on_startup=True,
)

# Планировщик: раз в день подтянуть курсы
celery_app.conf.beat_schedule = {
    "fetch-exchange-rates-daily": {
        "task": "app.tasks.fetch_exchange_rates",
        "schedule": crontab(hour=3, minute=0),  # 03:00 местного времени
        "options": {"queue": "default"},
    }
}
