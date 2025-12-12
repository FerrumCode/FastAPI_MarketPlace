import logging

from prometheus_client import Counter  # >>> METRICS
from app.celery_app import celery_app
from app.services.exchange import update_all_rates
from env import SERVICE_NAME  # >>> METRICS

logger = logging.getLogger(__name__)

RATES_TASK_RUNS_TOTAL = Counter(
    "celery_worker_rates_task_runs_total",
    "Number of times rates.update_exchange_rates task was invoked",
    ["service"],
)

RATES_TASK_RESULTS_TOTAL = Counter(
    "celery_worker_rates_task_results_total",
    "Results of rates.update_exchange_rates task",
    ["service", "result"],
)

RATES_TASK_RETRIES_TOTAL = Counter(
    "celery_worker_rates_task_retries_total",
    "Retries requested by rates.update_exchange_rates task",
    ["service", "reason"],
)

RATES_TASK_ERRORS_TOTAL = Counter(
    "celery_worker_rates_task_errors_total",
    "Errors in rates.update_exchange_rates task by type",
    ["service", "error_type"],
)


@celery_app.task(
    bind=True,
    name="rates.update_exchange_rates",
    max_retries=5,
    default_retry_delay=60,
)
def update_exchange_rates_stub(self) -> None:
    RATES_TASK_RUNS_TOTAL.labels(service=SERVICE_NAME).inc()

    try:
        update_all_rates()
        logger.info("Exchange rates updated via Celery task")
        RATES_TASK_RESULTS_TOTAL.labels(
            service=SERVICE_NAME,
            result="success",
        ).inc()
    except Exception as exc:
        RATES_TASK_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
            error_type="update_rates_error",
        ).inc()

        RATES_TASK_RETRIES_TOTAL.labels(
            service=SERVICE_NAME,
            reason="update_rates_error",
        ).inc()
        RATES_TASK_RESULTS_TOTAL.labels(
            service=SERVICE_NAME,
            result="retry_update_rates_error",
        ).inc()
        logger.exception(
            "Failed to update exchange rates, retrying (attempt %s of %s): %s",
            self.request.retries + 1,
            self.max_retries,
            exc,
        )
        raise self.retry(exc=exc)
