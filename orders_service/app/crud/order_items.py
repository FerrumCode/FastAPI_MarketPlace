from __future__ import annotations

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_item import OrderItem
from app.models.order import Order
from app.schemas.order_item import OrderItemCreate, OrderItemRead, OrderItemUpdate
from app.core.kafka import send_kafka_event
from env import KAFKA_ORDER_TOPIC, SERVICE_NAME
from app.core.metrics import ORDER_ITEMS_DB_OPERATIONS_TOTAL



async def get_order_item_from_db(id: str, db: AsyncSession):
    ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="get",
        status="attempt",
    ).inc()
    logger.info(
        "Fetching order item from DB. id='{id}'",
        id=id,
    )
    result = await db.execute(select(OrderItem).where(OrderItem.id == id))
    item = result.scalar_one_or_none()
    if not item:
        logger.warning(
            "Order item not found in DB. id='{id}'",
            id=id,
        )
        ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="get",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=404, detail="Order item not found")
    logger.info(
        "Successfully fetched order item from DB. id='{id}'",
        id=id,
    )
    ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="get",
        status="success",
    ).inc()
    return OrderItemRead.model_validate(item)


async def create_order_item_in_db(data: OrderItemCreate, db: AsyncSession):
    ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="create",
        status="attempt",
    ).inc()
    logger.info(
        "Attempt to create order item for order_id='{order_id}'",
        order_id=str(data.order_id),
    )
    order_res = await db.execute(select(Order).where(Order.id == data.order_id))
    if order_res.scalar_one_or_none() is None:
        logger.warning(
            "Order does not exist while creating order item. order_id='{order_id}'",
            order_id=str(data.order_id),
        )
        ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="create",
            status="order_not_found",
        ).inc()
        raise HTTPException(status_code=400, detail="Order does not exist")

    new_item = OrderItem(**data.dict())
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    logger.info(
        "Order item created successfully. item_id='{item_id}', order_id='{order_id}'",
        item_id=str(new_item.id),
        order_id=str(new_item.order_id),
    )
    ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="create",
        status="success",
    ).inc()

    await send_kafka_event(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_UPDATED",
            "order_id": str(new_item.order_id),
            "reason": "item_created",
        },
    )
    logger.info(
        "Kafka event 'ORDER_UPDATED' sent after order item creation. order_id='{order_id}'",
        order_id=str(new_item.order_id),
    )

    return OrderItemRead.model_validate(new_item)


async def update_order_item_in_db(id: str, data: OrderItemUpdate, db: AsyncSession):
    ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="update",
        status="attempt",
    ).inc()
    logger.info(
        "Attempt to update order item. id='{id}'",
        id=id,
    )
    result = await db.execute(select(OrderItem).where(OrderItem.id == id))
    item = result.scalar_one_or_none()
    if not item:
        logger.warning(
            "Order item not found in DB for update. id='{id}'",
            id=id,
        )
        ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="update",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=404, detail="Order item not found")

    for field, value in data.dict(exclude_unset=True).items():
        logger.debug(
            "Updating field '{field}' of order item '{id}' to '{value}'",
            field=field,
            id=id,
            value=value,
        )
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)

    logger.info(
        "Order item updated successfully. id='{id}', order_id='{order_id}'",
        id=id,
        order_id=str(item.order_id),
    )
    ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="update",
        status="success",
    ).inc()

    await send_kafka_event(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_UPDATED",
            "order_id": str(item.order_id),
            "reason": "item_updated",
        },
    )
    logger.info(
        "Kafka event 'ORDER_UPDATED' sent after order item update. order_id='{order_id}'",
        order_id=str(item.order_id),
    )

    return OrderItemRead.model_validate(item)


async def delete_order_item_from_db(id: str, db: AsyncSession):
    ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="delete",
        status="attempt",
    ).inc()
    logger.info(
        "Attempt to delete order item. id='{id}'",
        id=id,
    )
    result = await db.execute(select(OrderItem).where(OrderItem.id == id))
    item = result.scalar_one_or_none()
    if not item:
        logger.warning(
            "Order item not found in DB for deletion. id='{id}'",
            id=id,
        )
        ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="delete",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=404, detail="Order item not found")

    order_id = item.order_id
    await db.delete(item)
    await db.commit()

    logger.info(
        "Order item deleted successfully. id='{id}', order_id='{order_id}'",
        id=id,
        order_id=str(order_id),
    )
    ORDER_ITEMS_DB_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="delete",
        status="success",
    ).inc()

    await send_kafka_event(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_UPDATED",
            "order_id": str(order_id),
            "reason": "item_deleted",
        },
    )
    logger.info(
        "Kafka event 'ORDER_UPDATED' sent after order item deletion. order_id='{order_id}'",
        order_id=str(order_id),
    )

    return {"detail": "Order item deleted"}
