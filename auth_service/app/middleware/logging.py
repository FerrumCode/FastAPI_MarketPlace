import time
from loguru import logger
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000
        formatted_process_time = f"{process_time:.2f}"

        logger.info(
            f"request_path={request.url.path} "
            f"method={request.method} "
            f"status_code={response.status_code} "
            f"process_time_ms={formatted_process_time}"
        )

        return response
