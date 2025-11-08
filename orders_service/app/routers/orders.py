from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.kafka import kafka_producer
from app.db_depends import get_db
from app.dependencies.depend import (
    authentication_get_current_user,
    permission_required,
    bearer_scheme,
    user_owner_access_checker,
)
from app.schemas.order import OrderCreate, OrderOut, OrderStatusPatch
from app.service.orders import (
    create_order as svc_create_order,
    get_order as svc_get_order,
    delete_order as svc_delete_order,
    update_order_status as svc_update_order_status,
)
from env import KAFKA_ORDER_TOPIC, CURRENCY_BASE

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/",
             dependencies=[Depends(permission_required("can_create_order"))],
             response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authentication_get_current_user),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    bearer_header = f"Bearer {creds.credentials}"

    user_uuid = (
        current_user["id"]
        if isinstance(current_user["id"], UUID)
        else UUID(str(current_user["id"]))
    )

    async with db.begin():
        created_order = await svc_create_order(
            db,
            user_id=user_uuid,
            items_in=[item.model_dump() for item in payload.items],
            currency_base=CURRENCY_BASE,
            target_currency=payload.target_currency,
            auth_header=bearer_header,
        )

    order_full = await svc_get_order(db, created_order.id)
    if not order_full:
        raise HTTPException(status_code=500, detail="Order lost after creation")

    await kafka_producer.send(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_CREATED",
            "order_id": str(order_full.id),
            "user_id": str(order_full.user_id),
            "target_currency": payload.target_currency,
            "currency_base": CURRENCY_BASE,
            "items": [
                {
                    "product_id": str(i.product_id),
                    "quantity": i.quantity,
                    "unit_price": float(i.unit_price),
                }
                for i in order_full.items
            ],
            "cart_price": float(order_full.cart_price),
            "delivery_price": float(order_full.delivery_price),
            "total_price": float(order_full.total_price),
            "status": order_full.status,
        },
        key=str(order_full.id),
    )

    return order_full


@router.get("/{order_id}",
            dependencies=[Depends(permission_required("can_get_order"))],
            response_model=OrderOut)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(user_owner_access_checker),
):
    order = await svc_get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.delete("/{order_id}",
               dependencies=[Depends(permission_required("can_delete_order"))],
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(user_owner_access_checker),
):
    async with db.begin():
        ok = await svc_delete_order(db, order_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Order not found")

    await kafka_producer.send(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_UPDATED",
            "order_id": str(order_id),
            "status": "deleted",
        },
        key=str(order_id),
    )

    return None


@router.patch("/{order_id}",
              dependencies=[Depends(permission_required("can_patch_order_status"))],
              response_model=OrderOut)
async def patch_order_status(
    order_id: UUID,
    payload: OrderStatusPatch,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(user_owner_access_checker),
):
    async with db.begin():
        order_after = await svc_update_order_status(db, order_id, payload.status)
        if not order_after:
            raise HTTPException(status_code=404, detail="Order not found")

    await kafka_producer.send(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_UPDATED",
            "order_id": str(order_id),
            "status": payload.status,
        },
        key=str(order_id),
    )

    fresh = await svc_get_order(db, order_id)
    if not fresh:
        raise HTTPException(status_code=404, detail="Order not found")
    return fresh
