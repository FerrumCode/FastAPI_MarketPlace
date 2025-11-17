import logging

from app.celery_app import celery_app
from app.services.exchange import update_all_rates

logger = logging.getLogger(__name__)


@celery_app.task(name="rates.update_exchange_rates")
def update_exchange_rates_stub() -> None:
    update_all_rates()
    logger.info("Exchange rates stub updated via Celery task")
