from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.kafka import kafka_producer
from app.crud.orders import create_order, get_order, delete_order, update_order_status
from app.db_depends import get_db  # имя файла сохранено как у тебя
from app.dependencies.auth import get_current_user
from app.schemas.order import OrderCreate, OrderOut, OrderStatusPatch

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order_endpoint(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # создаём заказ
    async with db.begin():
        order = await create_order(
            db,
            user_id=current_user["id"] if isinstance(current_user["id"], UUID) else UUID(current_user["id"]),
            items_in=[item.model_dump() for item in payload.items],
            currency_base=settings.CURRENCY_BASE,
            target_currency=payload.target_currency,
        )

    # публикуем событие для воркера
    await kafka_producer.send(
        settings.KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_CREATED",
            "order_id": str(order.id),
            "user_id": str(order.user_id),
            "target_currency": payload.target_currency,
            "currency_base": settings.CURRENCY_BASE,
            "items": [
                {"product_id": str(i.product_id), "quantity": i.quantity, "unit_price": float(i.unit_price)}
                for i in order.items
            ],
            "cart_price": float(order.cart_price),
            "delivery_price": float(order.delivery_price),
            "total_price": float(order.total_price),
            "status": order.status,
        },
        key=str(order.id),
    )

    # повторно читаем с items для ответа
    async with db.begin():
        fresh = await get_order(db, order.id)
        if not fresh:
            raise HTTPException(status_code=500, detail="Order persisted but not found")
        return fresh


@router.get("/{order_id}", response_model=OrderOut)
async def get_order_endpoint(order_id: UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    order = await get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # (опционально) можно проверять право владельца: order.user_id == current_user["id"]
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order_endpoint(order_id: UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    async with db.begin():
        ok = await delete_order(db, order_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Order not found")
    # уведомление (необязательно)
    await kafka_producer.send(
        settings.KAFKA_ORDER_TOPIC,
        {"event": "ORDER_UPDATED", "order_id": str(order_id), "status": "deleted"},
        key=str(order_id),
    )
    return None


@router.patch("/{order_id}", response_model=OrderOut)
async def patch_order_status_endpoint(
    order_id: UUID,
    payload: OrderStatusPatch,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    async with db.begin():
        order = await update_order_status(db, order_id, payload.status)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

    await kafka_producer.send(
        settings.KAFKA_ORDER_TOPIC,
        {"event": "ORDER_UPDATED", "order_id": str(order_id), "status": payload.status},
        key=str(order_id),
    )

    # вернуть актуальную версию с items
    fresh = await get_order(db, order_id)
    return fresh
