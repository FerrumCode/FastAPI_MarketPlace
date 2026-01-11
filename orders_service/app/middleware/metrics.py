import time
from loguru import logger
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram

from env import SERVICE_NAME
from app.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        method = request.method
        path = request.url.path

        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            path = route.path

        response = await call_next(request)

        duration_seconds = time.time() - start_time

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
