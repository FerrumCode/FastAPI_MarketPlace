import logging
import os
import sys
import time
from pathlib import Path

from celery import Celery, signals
from env import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from loguru import logger
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, start_http_server
from prometheus_client import multiprocess


PROMETHEUS_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "/tmp/celery_prometheus_multiproc")
os.environ["PROMETHEUS_MULTIPROC_DIR"] = PROMETHEUS_MULTIPROC_DIR
METRICS_PORT = int(os.getenv("METRICS_PORT", "9000"))
_METRICS_SERVER_STARTED = False
_TASK_START_TIMES = {}


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.remove()
    logger.add(
        sys.stdout,
        format='{{"timestamp": "{time:YYYY-MM-DDTHH:mm:ssZ}", '
               '"level": "{level}", '
               '"service": "celery_worker_service", '
               '"message": "{message}"}}',
        level=log_level,
        serialize=True,
    )
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ("celery", "celery.app.trace", "kombu", "amqp"):
        log = logging.getLogger(name)
        log.handlers = [InterceptHandler()]
        log.propagate = False
        log.setLevel(log_level)


setup_logging()


def _cleanup_multiproc_dir() -> None:
    path = Path(PROMETHEUS_MULTIPROC_DIR)
    if path.exists():
        for child in path.iterdir():
            if child.is_file():
                child.unlink()
    else:
        path.mkdir(parents=True, exist_ok=True)


def _start_metrics_http_server() -> None:
    global _METRICS_SERVER_STARTED
    if _METRICS_SERVER_STARTED:
        return
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    try:
        start_http_server(METRICS_PORT, registry=registry)
        _METRICS_SERVER_STARTED = True
        logger.info("Prometheus /metrics HTTP server started on port {}", METRICS_PORT)
    except OSError as exc:
        logger.error("Failed to start Prometheus HTTP server on port {}: {}", METRICS_PORT, exc)


TASKS_STARTED = Counter(
    "celery_worker_tasks_started_total",
    "Number of Celery tasks started",
    ["task_name"],
)

TASKS_SUCCEEDED = Counter(
    "celery_worker_tasks_succeeded_total",
    "Number of Celery tasks succeeded",
    ["task_name"],
)

TASKS_FAILED = Counter(
    "celery_worker_tasks_failed_total",
    "Number of Celery tasks failed",
    ["task_name"],
)

TASKS_RETRIED = Counter(
    "celery_worker_tasks_retried_total",
    "Number of Celery task executions that ended with RETRY state",
    ["task_name"],
)

TASKS_FAILED_BY_EXCEPTION = Counter(
    "celery_worker_tasks_failed_by_exception_total",
    "Number of Celery task failures by exception type",
    ["task_name", "exc_type"],
)

TASKS_IN_PROGRESS = Gauge(
    "celery_worker_tasks_in_progress",
    "Number of Celery tasks currently running",
    ["task_name"],
)

TASK_RUNTIME = Histogram(
    "celery_worker_task_runtime_seconds",
    "Celery task runtime in seconds",
    ["task_name"],
)


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


@signals.worker_init.connect
def on_worker_init(**kwargs):
    _cleanup_multiproc_dir()
    logger.info("Celery worker init completed")


@signals.worker_ready.connect
def on_worker_ready(sender=None, **kwargs):
    _start_metrics_http_server()
    logger.info("Celery worker is ready. Sender: {}", sender)


@signals.worker_shutdown.connect
def on_worker_shutdown(sender=None, **kwargs):
    logger.info("Celery worker is shutting down. Sender: {}", sender)


@signals.task_prerun.connect
def on_task_prerun(task_id=None, task=None, args=None, kwargs=None, **_):
    task_name = getattr(task, "name", "unknown")
    _TASK_START_TIMES[task_id] = time.time()
    TASKS_STARTED.labels(task_name=task_name).inc()
    TASKS_IN_PROGRESS.labels(task_name=task_name).inc()
    logger.info("Task started: {task} [{id}]", task=task_name, id=task_id)


@signals.task_postrun.connect
def on_task_postrun(task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **_):
    task_name = getattr(task, "name", "unknown")
    start_time = _TASK_START_TIMES.pop(task_id, None)
    if start_time is not None:
        duration = time.time() - start_time
        TASK_RUNTIME.labels(task_name=task_name).observe(duration)
    TASKS_IN_PROGRESS.labels(task_name=task_name).dec()

    if state == "SUCCESS":
        TASKS_SUCCEEDED.labels(task_name=task_name).inc()
        logger.info(
            "Task finished successfully: {task} [{id}] (retval={retval})",
            task=task_name,
            id=task_id,
            retval=retval,
        )
    else:
        if state == "RETRY":
            TASKS_RETRIED.labels(task_name=task_name).inc()

        logger.warning(
            "Task finished with state {state}: {task} [{id}]",
            state=state,
            task=task_name,
            id=task_id,
        )


@signals.task_failure.connect
def on_task_failure(task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, sender=None, **_):
    task_name = getattr(sender, "name", "unknown")
    TASKS_FAILED.labels(task_name=task_name).inc()

    exc_type = type(exception).__name__ if exception is not None else "unknown"
    TASKS_FAILED_BY_EXCEPTION.labels(task_name=task_name, exc_type=exc_type).inc()

    logger.error(
        "Task failed: {task} [{id}] - {exc}\n{einfo}",
        task=task_name,
        id=task_id,
        exc=exception,
        einfo=einfo,
    )
