import uuid
import time
from loguru import logger
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS
from env import SERVICE_NAME


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        method = request.method

        path = request.url.path

        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            path = route.path

        with logger.contextualize(request_id=request_id):
            response = await call_next(request)

            process_time_ms = (time.time() - start_time) * 1000
            duration_seconds = process_time_ms / 1000.0

            logger.bind(
                request_path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                process_time_ms=round(process_time_ms, 2),
            ).info("http_request_processed")

            try:
                HTTP_REQUESTS_TOTAL.labels(
                    service=SERVICE_NAME,
                    method=method,
                    path=path,
                    status_code=str(response.status_code),
                ).inc()

                HTTP_REQUEST_DURATION_SECONDS.labels(
                    service=SERVICE_NAME,
                    method=method,
                    path=path,
                ).observe(duration_seconds)
            except Exception:
                logger.exception("Error updating Prometheus HTTP metrics")

            return response
