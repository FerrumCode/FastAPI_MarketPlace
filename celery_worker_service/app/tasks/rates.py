import logging

from app.celery_app import celery_app
from app.services.exchange import update_all_rates

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="rates.update_exchange_rates",
    max_retries=5,
    default_retry_delay=60,
)
def update_exchange_rates_stub(self) -> None:
    try:
        update_all_rates()
        logger.info("Exchange rates updated via Celery task")
    except Exception as exc:
        logger.exception(
            "Failed to update exchange rates, retrying (attempt %s of %s): %s",
            self.request.retries + 1,
            self.max_retries,
            exc,
        )
        raise self.retry(exc=exc)
