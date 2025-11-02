from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_db
from app.schemas.order import OrderCreate, OrderOut, OrderStatusPatch
from app.crud.orders import (
    get_all_orders_from_db,
    get_order_from_db,
    create_order_in_db,
    update_order_status_in_db,
    delete_order_from_db,
)
from app.dependencies.depend import authentication_get_current_user, permission_required

router = APIRouter(prefix="/orders_crud", tags=["Orders CRUD"])


@router.get("/",
            dependencies=[Depends(permission_required("can_get_all_orders"))],
            response_model=list[OrderOut])
async def get_all_orders(
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    user_id = user["id"]
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    return await get_all_orders_from_db(db, user_id)


@router.get("/{order_id}",
            dependencies=[Depends(permission_required("can_get_order"))],
            response_model=OrderOut)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    return await get_order_from_db(order_id, db)


@router.post("/",
             dependencies=[Depends(permission_required("can_create_order"))],
             response_model=OrderOut,
             status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    user_id = user["id"]
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    return await create_order_in_db(data, user_id, db)


@router.patch("/{order_id}",
              dependencies=[Depends(permission_required("can_update_order_status"))],
              response_model=OrderOut)
async def update_order_status(
    order_id: UUID,
    data: OrderStatusPatch,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    return await update_order_status_in_db(order_id, data, db)


@router.delete("/{order_id}",
               dependencies=[Depends(permission_required("can_delete_order"))])
async def delete_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    return await delete_order_from_db(order_id, db)
