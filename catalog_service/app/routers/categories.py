import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.category import Category
from app.db_depends import get_db
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.core.redis import get_redis
from app.crud.categories import (get_all_categories_from_db, delete_category_from_db,
                                 create_category_in_db, update_category_in_db)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[CategoryRead])
async def get_all_categories(db: AsyncSession = Depends(get_db)):
    return await get_all_categories_from_db(db)


@router.post("/", response_model=CategoryRead)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    return await create_category_in_db(category, db)


@router.put("/{id}", response_model=CategoryRead)
async def update_category(id: str, data: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    return await update_category_in_db(id, data, db)


@router.delete("/{id}")
async def delete_category(id: str, db: AsyncSession = Depends(get_db)):
    return await delete_category_from_db(id, db)
