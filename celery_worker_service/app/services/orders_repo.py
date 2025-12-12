from __future__ import annotations

import httpx
from loguru import logger
from prometheus_client import Counter

from env import ORDERS_SERVICE_URL, ORDERS_SERVICE_TOKEN, SERVICE_NAME
from app.schemas.order import FinalOrderPatch, OrderOut


ORDERS_REPO_REQUESTS_TOTAL = Counter(
    "celery_worker_orders_repo_requests_total",
    "HTTP requests from celery worker to Orders service",
    ["service", "method", "endpoint", "status"],
)

ORDERS_REPO_ERRORS_TOTAL = Counter(
    "celery_worker_orders_repo_errors_total",
    "Errors while calling Orders service from celery worker",
    ["service", "method", "endpoint", "error_type"],
)


def _get_auth_headers() -> dict[str, str]:
    if not ORDERS_SERVICE_TOKEN:
        logger.warning(
            "ORDERS_SERVICE_TOKEN is empty – requests to Orders service may fail",
        )
    return {"Authorization": f"Bearer {ORDERS_SERVICE_TOKEN}"}


async def patch_final_order(order_id: str, patch: FinalOrderPatch) -> OrderOut:
    url = f"{ORDERS_SERVICE_URL}/orders/make_final_order_with_delivery/{order_id}"
    endpoint = "/orders/make_final_order_with_delivery"

    payload = patch.model_dump(exclude_none=True, mode="json")

    logger.info(
        "Calling Orders Service PATCH {url} with payload={payload}",
        url=url,
        payload=payload,
    )
    ORDERS_REPO_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        method="PATCH",
        endpoint=endpoint,
        status="attempt",
    ).inc()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, json=payload, headers=_get_auth_headers())
            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException as exc:
        ORDERS_REPO_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
            method="PATCH",
            endpoint=endpoint,
            error_type="timeout",
        ).inc()
        raise
    except httpx.HTTPStatusError as exc:
        ORDERS_REPO_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
            method="PATCH",
            endpoint=endpoint,
            error_type="http_status_error",
        ).inc()
        raise
    except httpx.RequestError as exc:
        ORDERS_REPO_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
            method="PATCH",
            endpoint=endpoint,
            error_type="request_error",
        ).inc()
        raise
    except ValueError as exc:
        ORDERS_REPO_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
            method="PATCH",
            endpoint=endpoint,
            error_type="json_error",
        ).inc()
        raise
    except Exception as exc:
        ORDERS_REPO_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
            method="PATCH",
            endpoint=endpoint,
            error_type="unexpected_error",
        ).inc()
        raise

    ORDERS_REPO_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        method="PATCH",
        endpoint=endpoint,
        status=str(resp.status_code),
    ).inc()
    logger.info(
        "Orders Service PATCH completed. url={url}, status_code={status_code}",
        url=url,
        status_code=resp.status_code,
    )

    return OrderOut.model_validate(data)
