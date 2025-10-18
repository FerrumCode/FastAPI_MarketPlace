from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_item import OrderItem
from app.models.order import Order
from app.schemas.order_item import OrderItemCreate, OrderItemRead, OrderItemUpdate
from app.core.kafka import send_kafka_event
from app.core.config import settings


async def get_all_order_items_from_db(db: AsyncSession):
    result = await db.execute(select(OrderItem))
    items = result.scalars().all()
    return [OrderItemRead.model_validate(i) for i in items]


async def get_order_item_from_db(id: str, db: AsyncSession):
    result = await db.execute(select(OrderItem).where(OrderItem.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    return OrderItemRead.model_validate(item)


async def create_order_item_in_db(data: OrderItemCreate, db: AsyncSession):
    order_res = await db.execute(select(Order).where(Order.id == data.order_id))
    if order_res.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Order does not exist")

    new_item = OrderItem(**data.dict())
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    await send_kafka_event(
        settings.KAFKA_ORDER_TOPIC,
        {"event": "ORDER_UPDATED", "order_id": str(new_item.order_id), "reason": "item_created"},
    )

    return OrderItemRead.model_validate(new_item)


async def update_order_item_in_db(id: str, data: OrderItemUpdate, db: AsyncSession):
    result = await db.execute(select(OrderItem).where(OrderItem.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)

    await send_kafka_event(
        settings.KAFKA_ORDER_TOPIC,
        {"event": "ORDER_UPDATED", "order_id": str(item.order_id), "reason": "item_updated"},
    )

    return OrderItemRead.model_validate(item)


async def delete_order_item_from_db(id: str, db: AsyncSession):
    result = await db.execute(select(OrderItem).where(OrderItem.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")

    order_id = item.order_id
    await db.delete(item)
    await db.commit()

    await send_kafka_event(
        settings.KAFKA_ORDER_TOPIC,
        {"event": "ORDER_UPDATED", "order_id": str(order_id), "reason": "item_deleted"},
    )

    return {"detail": "Order item deleted"}
