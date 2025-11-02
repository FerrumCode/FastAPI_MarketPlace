from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_db
from app.schemas.order_item import OrderItemCreate, OrderItemRead, OrderItemUpdate
from app.crud.order_items import (
    get_all_order_items_from_db,
    get_order_item_from_db,
    create_order_item_in_db,
    update_order_item_in_db,
    delete_order_item_from_db,
)
from app.dependencies.depend import authentication_get_current_user

router = APIRouter(prefix="/order_items_crud", tags=["Order items CRUD"])


@router.get("/", response_model=list[OrderItemRead])
async def get_all_order_items(
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    return await get_all_order_items_from_db(db)


@router.get("/{id}", response_model=OrderItemRead)
async def get_order_item(
    id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    return await get_order_item_from_db(id, db)


@router.post("/", response_model=OrderItemRead)
async def create_order_item(
    data: OrderItemCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    return await create_order_item_in_db(data, db)


@router.put("/{id}", response_model=OrderItemRead)
async def update_order_item(
    id: str,
    data: OrderItemUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    return await update_order_item_in_db(id, data, db)


@router.delete("/{id}")
async def delete_order_item(
    id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    return await delete_order_item_from_db(id, db)
