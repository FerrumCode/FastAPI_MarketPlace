import uuid
import time
from loguru import logger
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        with logger.contextualize(request_id=request_id):
            try:
                response = await call_next(request)

                process_time_ms = (time.time() - start_time) * 1000

                logger.bind(
                    request_path=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    process_time_ms=round(process_time_ms, 2),
                ).info("http_request_processed")

                return response

            except Exception:
                process_time_ms = (time.time() - start_time) * 1000

                logger.bind(
                    request_path=request.url.path,
                    method=request.method,
                    status_code=500,
                    process_time_ms=round(process_time_ms, 2),
                ).exception("http_request_failed")

                raise
