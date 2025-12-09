from __future__ import annotations

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from loguru import logger
from prometheus_client import Counter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.clients import fetch_product
from app.core.kafka import send_kafka_event
from app.models.order import Order
from app.models.order_item import OrderItem
from app.schemas.order import OrderCreate, OrderOut, OrderStatusPatch

from env import KAFKA_ORDER_TOPIC, CURRENCY_BASE, SERVICE_NAME

ORDERS_DB_OPERATIONS_TOTAL = Counter(
    "orders_db_operations_total",
    "Orders DB operations",
    ["service", "operation", "status"],
)


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def get_order_from_db(order_id: UUID, db: AsyncSession) -> OrderOut:
    ORDERS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="get",
        status="attempt",
    ).inc()
    logger.info(
        "Fetching order from DB. order_id='{order_id}'",
        order_id=str(order_id),
    )
    q = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    res = await db.execute(q)
    order = res.scalar_one_or_none()
    if not order:
        logger.warning(
            "Order not found in DB. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_DB_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="get",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=404, detail="Order not found")
    logger.info(
        "Successfully fetched order from DB. order_id='{order_id}'",
        order_id=str(order_id),
    )
    ORDERS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="get",
        status="success",
    ).inc()
    return OrderOut.model_validate(order)


async def create_order_in_db(
    data: OrderCreate,
    user_id: UUID,
    db: AsyncSession,
) -> OrderOut:
    ORDERS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="create",
        status="attempt",
    ).inc()
    logger.info(
        "Attempt to create order in DB for user_id='{user_id}' with {items_count} items",
        user_id=str(user_id),
        items_count=len(data.items) if data.items else 0,
    )
    if not data.items:
        logger.warning(
            "Attempt to create order without items for user_id='{user_id}'",
            user_id=str(user_id),
        )
        ORDERS_DB_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="create",
            status="no_items",
        ).inc()
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    product_ids = [i.product_id for i in data.items]
    logger.debug(
        "Fetching products from Catalog Service for new order. product_ids={product_ids}",
        product_ids=[str(pid) for pid in product_ids],
    )
    products = await asyncio.gather(*[fetch_product(pid) for pid in product_ids], return_exceptions=True)

    prices: dict[UUID, Decimal] = {}
    for idx, p in enumerate(products):
        if isinstance(p, Exception):
            logger.error(
                "Failed to fetch product '{product_id}' from Catalog Service while creating order: {error}",
                product_id=str(product_ids[idx]),
                error=str(p),
            )
            ORDERS_DB_OPERATIONS_TOTAL.labels(
                service=SERVICE_NAME,
                operation="create",
                status="product_fetch_failed",
            ).inc()
            raise HTTPException(status_code=400, detail=f"Failed to fetch product {product_ids[idx]}: {p}")
        try:
            pid = UUID(p["id"]) if isinstance(p["id"], str) else p["id"]
            price = Decimal(str(p["price"]))
        except Exception:
            logger.error(
                "Bad product payload from Catalog Service for product '{product_id}' while creating order",
                product_id=str(product_ids[idx]),
            )
            ORDERS_DB_OPERATIONS_TOTAL.labels(
                service=SERVICE_NAME,
                operation="create",
                status="bad_product_payload",
            ).inc()
            raise HTTPException(status_code=400, detail=f"Bad product payload from Catalog for {product_ids[idx]}")
        prices[pid] = _money(price)
        logger.debug(
            "Product '{product_id}' price set to {price}",
            product_id=str(pid),
            price=float(prices[pid]),
        )

    cart_total = Decimal("0.00")
    order_items: list[OrderItem] = []

    for item in data.items:
        pid = item.product_id
        qty = int(item.quantity)
        if pid not in prices:
            logger.error(
                "Product '{product_id}' not found in prepared prices while creating order",
                product_id=str(pid),
            )
            ORDERS_DB_OPERATIONS_TOTAL.labels(
                service=SERVICE_NAME,
                operation="create",
                status="product_not_in_prices",
            ).inc()
            raise HTTPException(status_code=400, detail=f"Product not found in Catalog: {pid}")
        unit_price = prices[pid]
        cart_total += unit_price * qty
        logger.debug(
            "Adding order item product_id='{product_id}', qty={qty}, unit_price={unit_price}",
            product_id=str(pid),
            qty=qty,
            unit_price=float(unit_price),
        )
        order_items.append(
            OrderItem(
                product_id=pid,
                quantity=qty,
                unit_price=float(unit_price),
            )
        )

    cart_total = _money(cart_total)
    logger.info(
        "Calculated cart_total={cart_total} for new order of user_id='{user_id}'",
        cart_total=float(cart_total),
        user_id=str(user_id),
    )

    order = Order(
        user_id=user_id,
        status="created",
        delivery_price=0.0,
        cart_price=float(cart_total),
        total_price=float(cart_total),
        items=order_items,
    )

    db.add(order)
    await db.commit()
    logger.info(
        "Order persisted in DB. order_id='{order_id}', user_id='{user_id}'",
        order_id=str(order.id),
        user_id=str(user_id),
    )

    q = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    fresh = (await db.execute(q)).scalar_one()
    logger.info(
        "Fetched fresh order from DB after creation. order_id='{order_id}'",
        order_id=str(fresh.id),
    )

    await send_kafka_event(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_CREATED",
            "order_id": str(fresh.id),
            "user_id": str(fresh.user_id),
            "target_currency": data.target_currency,
            "currency_base": CURRENCY_BASE,
            "items": [
                {"product_id": str(i.product_id), "quantity": i.quantity, "unit_price": float(i.unit_price)}
                for i in fresh.items
            ],
            "cart_price": float(fresh.cart_price),
            "delivery_price": float(fresh.delivery_price),
            "total_price": float(fresh.total_price),
            "status": fresh.status,
        },
    )
    logger.info(
        "Kafka event 'ORDER_CREATED' sent after order creation. order_id='{order_id}'",
        order_id=str(fresh.id),
    )

    ORDERS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="create",
        status="success",
    ).inc()
    return OrderOut.model_validate(fresh)


async def update_order_status_in_db(order_id: UUID, data: OrderStatusPatch, db: AsyncSession) -> OrderOut:
    ORDERS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="update_status",
        status="attempt",
    ).inc()
    logger.info(
        "Attempt to update order status in DB. order_id='{order_id}', new_status='{status}'",
        order_id=str(order_id),
        status=data.status,
    )
    q = (
        update(Order)
        .where(Order.id == order_id)
        .values(status=data.status)
        .returning(Order)
    )
    res = await db.execute(q)
    updated = res.scalar_one_or_none()
    if not updated:
        logger.warning(
            "Order not found in DB for status update. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_DB_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="update_status",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=404, detail="Order not found")
    await db.commit()
    logger.info(
        "Order status updated in DB. order_id='{order_id}', new_status='{status}'",
        order_id=str(order_id),
        status=data.status,
    )

    q2 = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    fresh = (await db.execute(q2)).scalar_one()
    logger.info(
        "Fetched fresh order from DB after status update. order_id='{order_id}'",
        order_id=str(order_id),
    )

    await send_kafka_event(
        KAFKA_ORDER_TOPIC,
        {"event": "ORDER_UPDATED", "order_id": str(order_id), "status": data.status},
    )
    logger.info(
        "Kafka event 'ORDER_UPDATED' sent after order status update. order_id='{order_id}'",
        order_id=str(order_id),
    )

    ORDERS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="update_status",
        status="success",
    ).inc()
    return OrderOut.model_validate(fresh)


async def delete_order_from_db(order_id: UUID, db: AsyncSession) -> dict:
    ORDERS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="delete",
        status="attempt",
    ).inc()
    logger.info(
        "Attempt to delete order from DB. order_id='{order_id}'",
        order_id=str(order_id),
    )
    q = select(Order).where(Order.id == order_id)
    res = await db.execute(q)
    order = res.scalar_one_or_none()
    if not order:
        logger.warning(
            "Order not found in DB for deletion. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_DB_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="delete",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=404, detail="Order not found")

    await db.delete(order)
    await db.commit()
    logger.info(
        "Order deleted from DB. order_id='{order_id}'",
        order_id=str(order_id),
    )
    ORDERS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="delete",
        status="success",
    ).inc()

    await send_kafka_event(
        KAFKA_ORDER_TOPIC,
        {"event": "ORDER_UPDATED", "order_id": str(order_id), "status": "deleted"},
    )
    logger.info(
        "Kafka event 'ORDER_UPDATED' sent after order deletion. order_id='{order_id}'",
        order_id=str(order_id),
    )

    return {"detail": "Order deleted"}
