import time
from loguru import logger
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS
from env import SERVICE_NAME


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        method = request.method
        path = request.url.path
        status_code_str = "500"

        try:
            response = await call_next(request)
            status_code_str = str(response.status_code)
            return response
        finally:
            try:
                route = request.scope.get("route")
                if route and hasattr(route, "path"):
                    path = route.path
            except Exception:
                logger.opt(exception=True).debug(
                    "Failed to resolve route template for metrics; using raw path"
                )

            duration_seconds = time.time() - start_time

            try:
                HTTP_REQUESTS_TOTAL.labels(
                    service=SERVICE_NAME,
                    method=method,
                    path=path,
                    status_code=status_code_str,
                ).inc()

                HTTP_REQUEST_DURATION_SECONDS.labels(
                    service=SERVICE_NAME,
                    method=method,
                    path=path,
                ).observe(duration_seconds)
            except Exception:
                logger.exception("Error updating Prometheus HTTP metrics")
