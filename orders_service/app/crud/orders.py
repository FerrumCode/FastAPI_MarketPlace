from __future__ import annotations

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.clients import fetch_product
from app.core.kafka import send_kafka_event
from app.core.config import settings
from app.models.order import Order
from app.models.order_item import OrderItem
from app.schemas.order import OrderCreate, OrderOut, OrderStatusPatch


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def get_all_orders_from_db(db: AsyncSession, user_id: UUID) -> list[OrderOut]:
    q = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
    )
    res = await db.execute(q)
    orders = res.scalars().all()
    return [OrderOut.model_validate(o) for o in orders]


async def get_order_from_db(order_id: UUID, db: AsyncSession) -> OrderOut:
    q = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    res = await db.execute(q)
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderOut.model_validate(order)


async def create_order_in_db(data: OrderCreate, user_id: UUID, db: AsyncSession) -> OrderOut:
    if not data.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    product_ids = [i.product_id for i in data.items]
    products = await asyncio.gather(*[fetch_product(pid) for pid in product_ids], return_exceptions=True)

    prices: dict[UUID, Decimal] = {}
    for idx, p in enumerate(products):
        if isinstance(p, Exception):
            raise HTTPException(status_code=400, detail=f"Failed to fetch product {product_ids[idx]}: {p}")
        try:
            pid = UUID(p["id"]) if isinstance(p["id"], str) else p["id"]
            price = Decimal(str(p["price"]))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Bad product payload from Catalog for {product_ids[idx]}")
        prices[pid] = _money(price)

    cart_total = Decimal("0.00")
    order_items: list[OrderItem] = []

    for item in data.items:
        pid = item.product_id
        qty = int(item.quantity)
        if pid not in prices:
            raise HTTPException(status_code=400, detail=f"Product not found in Catalog: {pid}")
        unit_price = prices[pid]
        cart_total += unit_price * qty
        order_items.append(
            OrderItem(
                product_id=pid,
                quantity=qty,
                unit_price=float(unit_price),
            )
        )

    cart_total = _money(cart_total)

    order = Order(
        user_id=user_id,
        status="created",
        delivery_price=float(Decimal("0.00")),
        cart_price=float(cart_total),
        total_price=float(cart_total),
        items=order_items,
    )

    db.add(order)
    await db.commit()

    q = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    fresh = (await db.execute(q)).scalar_one()

    await send_kafka_event(
        settings.KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_CREATED",
            "order_id": str(fresh.id),
            "user_id": str(fresh.user_id),
            "target_currency": data.target_currency,
            "currency_base": settings.CURRENCY_BASE,
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

    return OrderOut.model_validate(fresh)


async def update_order_status_in_db(order_id: UUID, data: OrderStatusPatch, db: AsyncSession) -> OrderOut:
    q = (
        update(Order)
        .where(Order.id == order_id)
        .values(status=data.status)
        .returning(Order)
    )
    res = await db.execute(q)
    updated = res.scalar_one_or_none()
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.commit()

    q2 = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    fresh = (await db.execute(q2)).scalar_one()

    await send_kafka_event(
        settings.KAFKA_ORDER_TOPIC,
        {"event": "ORDER_UPDATED", "order_id": str(order_id), "status": data.status},
    )

    return OrderOut.model_validate(fresh)


async def delete_order_from_db(order_id: UUID, db: AsyncSession) -> dict:
    q = select(Order).where(Order.id == order_id)
    res = await db.execute(q)
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    await db.delete(order)
    await db.commit()

    await send_kafka_event(
        settings.KAFKA_ORDER_TOPIC,
        {"event": "ORDER_UPDATED", "order_id": str(order_id), "status": "deleted"},
    )

    return {"detail": "Order deleted"}
