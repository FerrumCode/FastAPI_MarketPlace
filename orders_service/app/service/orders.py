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
    auth_header: str | None = None,
) -> Order:
    """
    Создаёт заказ:
    - тянет каждый product из Catalog Service с пробрасыванием токена
    - считает cart_total
    - сохраняет Order и OrderItem[]
    """

    if not items_in:
        raise HTTPException(
            status_code=400,
            detail="Order must contain at least one item",
        )

    # product_id из запроса -> UUID
    product_ids: list[UUID] = [
        UUID(str(item["product_id"])) for item in items_in
    ]

    # параллельно стучимся в Catalog Service за каждым товаром
    products = await asyncio.gather(
        *[
            fetch_product(pid, auth_header=auth_header)
            for pid in product_ids
        ],
        return_exceptions=True,
    )

    # мапа product_id -> Decimal(price)
    prices: dict[UUID, Decimal] = {}
    for idx, p in enumerate(products):
        if isinstance(p, Exception):
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch product {product_ids[idx]}: {p}",
            )

        try:
            pid = UUID(str(p["id"]))
            price = Decimal(str(p["price"]))
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Bad product payload from Catalog for {product_ids[idx]}",
            )

        prices[pid] = price

    # считаем корзину и готовим OrderItem[]
    cart_total = Decimal("0.00")
    order_items: list[OrderItem] = []

    for raw_item in items_in:
        pid = UUID(str(raw_item["product_id"]))
        qty = int(raw_item["quantity"])

        if pid not in prices:
            raise HTTPException(
                status_code=400,
                detail=f"Product not found in Catalog: {pid}",
            )

        unit_price = _to_money(prices[pid])
        line_total = unit_price * qty
        cart_total += line_total

        order_items.append(
            OrderItem(
                product_id=pid,
                quantity=qty,
                unit_price=float(unit_price),  # в БД float, считаем в Decimal
            )
        )

    cart_total = _to_money(cart_total)

    order = Order(
        user_id=user_id,
        status="created",
        delivery_price=float(Decimal("0.00")),
        cart_price=float(cart_total),
        total_price=float(cart_total),  # воркер потом добавит доставку и конвертацию
        items=order_items,
    )

    session.add(order)
    await session.flush()    # получили id
    await session.refresh(order)

    return order


async def get_order(session: AsyncSession, order_id: UUID) -> Order | None:
    q = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    res = await session.execute(q)
    return res.scalar_one_or_none()


async def delete_order(session: AsyncSession, order_id: UUID) -> bool:
    q = delete(Order).where(Order.id == order_id)
    res = await session.execute(q)
    return res.rowcount > 0


async def update_order_status(
    session: AsyncSession,
    order_id: UUID,
    status: str,
) -> Order | None:
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
