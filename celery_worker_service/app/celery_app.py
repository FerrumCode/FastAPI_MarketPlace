from celery import Celery

from env import CELERY_BROKER_URL, CELERY_RESULT_BACKEND


celery_app = Celery("celery_worker_service")

celery_app.conf.broker_url = CELERY_BROKER_URL
celery_app.conf.result_backend = CELERY_RESULT_BACKEND

celery_app.conf.task_default_queue = "celery_worker_service"

celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True


celery_app.conf.imports = (
    "app.tasks.orders",
    "app.tasks.rates",
)

celery_app.conf.beat_schedule = {
    "update-exchange-rates-every-30-min": {
        "task": "rates.update_exchange_rates",
        "schedule": 60 * 30,
    },
}

celery_app.autodiscover_tasks(["app.tasks"])
