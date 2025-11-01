from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product
from app.db_depends import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.core.kafka import send_kafka_event
from app.crud.products import (get_all_products_from_db, create_product_in_db, update_product_in_db,
                               get_product_from_db, delete_product_form_db)
from app.dependencies.depend import get_current_user, permission_required


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductRead])
async def get_all_products(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
   return await get_all_products_from_db(db)


@router.get("/{id}", response_model=ProductRead)
async def get_product(
    id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    return await get_product_from_db(id, db)


@router.post("/",
             dependencies=[Depends(permission_required("catalog_service - products - create_product"))],
             response_model=ProductRead)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    return await create_product_in_db(data, db)


@router.put("/{id}",
            dependencies=[Depends(permission_required("catalog_service - products - update_product"))],
            response_model=ProductRead)
async def update_product(
    id: str,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    return await update_product_in_db(id, data, db)


@router.delete("/{id}",
               dependencies=[Depends(permission_required("catalog_service - products - delete_product"))])
async def delete_product(
    id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    return await delete_product_form_db(id, db)
