from __future__ import annotations

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException
from loguru import logger
from prometheus_client import Counter
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.clients import fetch_product
from app.models.order import Order
from app.models.order_item import OrderItem
from env import SERVICE_NAME

ORDERS_SERVICE_OPERATIONS_TOTAL = Counter(
    "orders_service_operations_total",
    "Order service operations",
    ["service", "operation", "status"],
)


def _to_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def create_order(
    session: AsyncSession,
    user_id: UUID,
    items_in: Sequence[dict],
    currency_base: str,
    target_currency: str,
    auth_header: str | None = None,
) -> Order:
    ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="create",
        status="attempt",
    ).inc()
    logger.info(
        "Service create_order called for user_id='{user_id}' with {items_count} items",
        user_id=str(user_id),
        items_count=len(items_in) if items_in else 0,
    )
    if not items_in:
        logger.warning(
            "Service create_order called without items for user_id='{user_id}'",
            user_id=str(user_id),
        )
        ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="create",
            status="no_items",
        ).inc()
        raise HTTPException(
            status_code=400,
            detail="Order must contain at least one item",
        )

    product_ids: list[UUID] = [
        UUID(str(item["product_id"])) for item in items_in
    ]
    logger.debug(
        "Service create_order fetching products from Catalog. product_ids={product_ids}",
        product_ids=[str(pid) for pid in product_ids],
    )

    products = await asyncio.gather(
        *[
            fetch_product(pid, auth_header=auth_header)
            for pid in product_ids
        ],
        return_exceptions=True,
    )

    prices: dict[UUID, Decimal] = {}
    for idx, p in enumerate(products):
        if isinstance(p, Exception):
            logger.error(
                "Service create_order failed to fetch product '{product_id}': {error}",
                product_id=str(product_ids[idx]),
                error=str(p),
            )
            ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
                service=SERVICE_NAME,
                operation="create",
                status="product_fetch_failed",
            ).inc()
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch product {product_ids[idx]}: {p}",
            )

        try:
            pid = UUID(str(p["id"]))
            price = Decimal(str(p["price"]))
        except Exception:
            logger.error(
                "Service create_order received bad product payload from Catalog for '{product_id}'",
                product_id=str(product_ids[idx]),
            )
            ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
                service=SERVICE_NAME,
                operation="create",
                status="bad_product_payload",
            ).inc()
            raise HTTPException(
                status_code=400,
                detail=f"Bad product payload from Catalog for {product_ids[idx]}",
            )

        prices[pid] = price
        logger.debug(
            "Service create_order set price for product '{product_id}' to {price}",
            product_id=str(pid),
            price=float(price),
        )

    cart_total = Decimal("0.00")
    order_items: list[OrderItem] = []

    for raw_item in items_in:
        pid = UUID(str(raw_item["product_id"]))

        qty = int(raw_item["quantity"])

        if pid not in prices:
            logger.error(
                "Service create_order: product '{product_id}' not found in prepared prices",
                product_id=str(pid),
            )
            ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
                service=SERVICE_NAME,
                operation="create",
                status="product_not_in_prices",
            ).inc()
            raise HTTPException(
                status_code=400,
                detail=f"Product not found in Catalog: {pid}",
            )

        unit_price = _to_money(prices[pid])
        line_total = unit_price * qty
        cart_total += line_total
        logger.debug(
            "Service create_order adding item. product_id='{product_id}', qty={qty}, unit_price={unit_price}, line_total={line_total}",
            product_id=str(pid),
            qty=qty,
            unit_price=float(unit_price),
            line_total=float(line_total),
        )

        order_items.append(
            OrderItem(
                product_id=pid,
                quantity=qty,
                unit_price=float(unit_price),
            )
        )

    cart_total = _to_money(cart_total)
    logger.info(
        "Service create_order calculated cart_total={cart_total} for user_id='{user_id}'",
        cart_total=float(cart_total),
        user_id=str(user_id),
    )

    order = Order(
        user_id=user_id,
        status="created",
        delivery_price=float(Decimal("0.00")),
        cart_price=float(cart_total),
        total_price=float(cart_total),
        items=order_items,
    )

    session.add(order)
    await session.flush()
    await session.refresh(order)
    logger.info(
        "Service create_order persisted order. order_id='{order_id}', user_id='{user_id}'",
        order_id=str(order.id),
        user_id=str(user_id),
    )

    ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="create",
        status="success",
    ).inc()
    return order


async def get_order(session: AsyncSession, order_id: UUID) -> Order | None:
    ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="get",
        status="attempt",
    ).inc()
    logger.info(
        "Service get_order called. order_id='{order_id}'",
        order_id=str(order_id),
    )
    q = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    res = await session.execute(q)
    order = res.scalar_one_or_none()
    logger.info(
        "Service get_order completed. order_id='{order_id}', found={found}",
        order_id=str(order_id),
        found=bool(order),
    )
    ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="get",
        status="success",
    ).inc()
    return order


async def delete_order(session: AsyncSession, order_id: UUID) -> bool:
    ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="delete",
        status="attempt",
    ).inc()
    logger.info(
        "Service delete_order called. order_id='{order_id}'",
        order_id=str(order_id),
    )
    q = delete(Order).where(Order.id == order_id)
    res = await session.execute(q)
    deleted = res.rowcount > 0
    logger.info(
        "Service delete_order completed. order_id='{order_id}', deleted={deleted}",
        order_id=str(order_id),
        deleted=deleted,
    )
    ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="delete",
        status="success",
    ).inc()
    return deleted


async def update_order_status(
    session: AsyncSession,
    order_id: UUID,
    status: str,
) -> Order | None:
    ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="update_status",
        status="attempt",
    ).inc()
    logger.info(
        "Service update_order_status called. order_id='{order_id}', new_status='{status}'",
        order_id=str(order_id),
        status=status,
    )
    q = (
        update(Order)
        .where(Order.id == order_id)
        .values(status=status)
        .returning(Order)
    )
    res = await session.execute(q)
    order = res.scalar_one_or_none()
    if order:
        logger.info(
            "Service update_order_status updated order. order_id='{order_id}', new_status='{status}'",
            order_id=str(order_id),
            status=status,
        )
        await session.flush()
        await session.refresh(order)
        ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="update_status",
            status="success",
        ).inc()
    else:
        logger.warning(
            "Service update_order_status: order not found. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_SERVICE_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="update_status",
            status="not_found",
        ).inc()
    return order
