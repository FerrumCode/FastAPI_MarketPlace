from __future__ import annotations

import logging

import httpx

from env import ORDERS_SERVICE_URL, ORDERS_SERVICE_TOKEN
from app.schemas.order import FinalOrderPatch, OrderOut

logger = logging.getLogger(__name__)


def _get_auth_headers() -> dict[str, str]:
    if not ORDERS_SERVICE_TOKEN:
        logger.warning("ORDERS_SERVICE_TOKEN is empty – requests to Orders service may fail")
    return {"Authorization": f"Bearer {ORDERS_SERVICE_TOKEN}"}


def patch_final_order(order_id: str, patch: FinalOrderPatch) -> OrderOut:
    url = f"{ORDERS_SERVICE_URL}/orders/make_final_order_with_delivery/{order_id}"

    payload = patch.model_dump(exclude_none=True, mode="json")

    logger.info("Calling Orders Service PATCH %s with payload=%s", url, payload)

    with httpx.Client(timeout=10.0) as client:
        resp = client.patch(url, json=payload, headers=_get_auth_headers())
        resp.raise_for_status()
        data = resp.json()

    return OrderOut.model_validate(data)
