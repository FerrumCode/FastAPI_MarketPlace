import logging
import os
import sys
import time
from pathlib import Path
import threading
from http import HTTPStatus
from http.server import HTTPServer
from socketserver import ThreadingMixIn

from celery import Celery, signals
from env import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    METRICS_PORT,
    PROMETHEUS_MULTIPROC_DIR,
    METRICS_BEARER_TOKEN_FILE,
)
from loguru import logger
from prometheus_client import multiprocess
from prometheus_client.exposition import MetricsHandler
from app.core.metrics import (
    TASKS_STARTED,
    TASKS_SUCCEEDED,
    TASKS_FAILED,
    TASKS_RETRIED,
    TASKS_FAILED_BY_EXCEPTION,
    TASKS_IN_PROGRESS,
    TASK_RUNTIME,
)


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


def _load_metrics_bearer_token() -> str:
    try:
        with open(METRICS_BEARER_TOKEN_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        logger.exception("Failed to read metrics bearer token file: {}", METRICS_BEARER_TOKEN_FILE)
        return ""


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def _start_metrics_http_server() -> None:
    global _METRICS_SERVER_STARTED
    if _METRICS_SERVER_STARTED:
        return

    token = _load_metrics_bearer_token()
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)

    class _AuthMetricsHandler(MetricsHandler):
        pass

    _AuthMetricsHandler.registry = registry

    def _unauthorized(handler: MetricsHandler) -> None:
        handler.send_response(HTTPStatus.UNAUTHORIZED)
        handler.send_header("WWW-Authenticate", 'Bearer realm="metrics"')
        handler.end_headers()

    def _not_found(handler: MetricsHandler) -> None:
        handler.send_response(HTTPStatus.NOT_FOUND)
        handler.end_headers()

    def do_GET(self: MetricsHandler) -> None:
        if self.path != "/metrics":
            _not_found(self)
            return

        auth = self.headers.get("Authorization", "")
        if not token or auth != f"Bearer {token}":
            _unauthorized(self)
            return

        super(_AuthMetricsHandler, self).do_GET()

    _AuthMetricsHandler.do_GET = do_GET

    def _run() -> None:
        try:
            server = _ThreadingHTTPServer(("0.0.0.0", METRICS_PORT), _AuthMetricsHandler)
            logger.info("Protected Prometheus /metrics HTTP server started on port {}", METRICS_PORT)
            server.serve_forever()
        except OSError as exc:
            logger.error("Failed to start Prometheus HTTP server on port {}: {}", METRICS_PORT, exc)

    threading.Thread(target=_run, daemon=True).start()
    _METRICS_SERVER_STARTED = True



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
