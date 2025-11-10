from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import select
from app.models.order import Order

from app.db_depends import get_db
from app.schemas.order_item import OrderItemCreate, OrderItemRead, OrderItemUpdate
from app.crud.order_items import (
    get_order_item_from_db,
    create_order_item_in_db,
    update_order_item_in_db,
    delete_order_item_from_db,
)
from app.dependencies.depend import authentication_get_current_user, permission_required

router = APIRouter(prefix="/order_items_crud", tags=["Order items CRUD"])



@router.get("/{id}",
            response_model=OrderItemRead)
async def get_order_item(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authentication_get_current_user),
):
    order_item = await get_order_item_from_db(id, db)
    if not order_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    owner_id = await db.scalar(
        select(Order.user_id).where(Order.id == order_item.order_id)
    )
    if owner_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_id = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (owner_id != user_id) and ("can_force_rights" not in perms):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )
    return order_item


@router.post("/",
             dependencies=[Depends(permission_required("can_create_order_item"))],
             response_model=OrderItemRead)
async def create_order_item(
    data: OrderItemCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    return await create_order_item_in_db(data, db)


@router.put("/{id}",
            dependencies=[Depends(permission_required("can_update_order_item"))],
            response_model=OrderItemRead)
async def update_order_item(
    id: str,
    data: OrderItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authentication_get_current_user),
):
    order_item = await get_order_item_from_db(id, db)
    if not order_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    owner_id = await db.scalar(
        select(Order.user_id).where(Order.id == order_item.order_id)
    )
    if owner_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_id = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (owner_id != user_id) and ("can_force_rights" not in perms):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )
    return await update_order_item_in_db(id, data, db)


@router.delete("/{id}",
               dependencies=[Depends(permission_required("can_delete_order_item"))])
async def delete_order_item(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authentication_get_current_user),
):
    order_item = await get_order_item_from_db(id, db)
    if not order_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    owner_id = await db.scalar(
        select(Order.user_id).where(Order.id == order_item.order_id)
    )
    if owner_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_id = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (owner_id != user_id) and ("can_force_rights" not in perms):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )
    return await delete_order_item_from_db(id, db)