from __future__ import annotations

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.clients import fetch_product
from app.models.order import Order
from app.models.order_item import OrderItem


def _to_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def create_order(
    session: AsyncSession,
    user_id: UUID,
    items_in: Sequence[dict],
    currency_base: str,
    target_currency: str,
) -> Order:
    """
    1) тянем товары из каталога
    2) считаем cart_price (без доставки) в базовой валюте каталога
    3) сохраняем заказ со статусом 'created' (delivery_price=0, total=cart_price)
    4) возвращаем Order
    """
    if not items_in:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    # Параллельно тянем товары
    product_ids = [item["product_id"] for item in items_in]
    products = await asyncio.gather(*[fetch_product(pid) for pid in product_ids], return_exceptions=True)

    # Собираем map product_id -> price
    prices: dict[UUID, Decimal] = {}
    for idx, p in enumerate(products):
        if isinstance(p, Exception):
            raise HTTPException(status_code=400, detail=f"Failed to fetch product {product_ids[idx]}: {p}")
        try:
            pid = UUID(p["id"]) if isinstance(p["id"], str) else p["id"]
            price = Decimal(str(p["price"]))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Bad product payload from Catalog for {product_ids[idx]}")
        prices[pid] = price

    # Счёт корзины
    cart_total = Decimal("0.00")
    order_items: list[OrderItem] = []

    for item in items_in:
        pid: UUID = item["product_id"]
        qty: int = int(item["quantity"])
        if pid not in prices:
            raise HTTPException(status_code=400, detail=f"Product not found in Catalog: {pid}")
        unit_price = _to_money(prices[pid])
        line_total = unit_price * qty
        cart_total += line_total

        order_items.append(
            OrderItem(
                product_id=pid,
                quantity=qty,
                unit_price=float(unit_price),  # твоя модель хранит float; считаем Decimal и приводим
            )
        )

    cart_total = _to_money(cart_total)

    order = Order(
        user_id=user_id,
        status="created",
        delivery_price=float(Decimal("0.00")),
        cart_price=float(cart_total),
        total_price=float(cart_total),  # воркер потом обновит total с доставкой и конвертацией
        items=order_items,
    )

    session.add(order)
    await session.flush()
    await session.refresh(order)
    return order


async def get_order(session: AsyncSession, order_id: UUID) -> Order | None:
    q = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    res = await session.execute(q)
    return res.scalar_one_or_none()


async def delete_order(session: AsyncSession, order_id: UUID) -> bool:
    q = delete(Order).where(Order.id == order_id)
    res = await session.execute(q)
    return res.rowcount > 0


async def update_order_status(session: AsyncSession, order_id: UUID, status: str) -> Order | None:
    q = (
        update(Order)
        .where(Order.id == order_id)
        .values(status=status)
        .returning(Order)
    )
    res = await session.execute(q)
    order = res.scalar_one_or_none()
    if order:
        await session.flush()
        await session.refresh(order)
    return order
