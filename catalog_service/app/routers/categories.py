from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio.client import Redis

from app.dependencies.depend import authentication_get_current_user, permission_required
from app.db_depends import get_db
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.core.redis import get_redis
from app.crud.categories import (
    get_category_by_id_or_name,
    delete_category_from_db,
    create_category_in_db,
    update_category_in_db,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/",
            response_model=CategoryRead)
async def get_category(
    id: Optional[str] = None,
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user=Depends(authentication_get_current_user),
):
    return await get_category_by_id_or_name(db, redis, id=id, name=name)


@router.post("/",
             dependencies=[Depends(permission_required("can_create_category"))],
             response_model=CategoryRead)
async def create_category(category: CategoryCreate,
                          db: AsyncSession = Depends(get_db),
                          redis: Redis = Depends(get_redis)):
    return await create_category_in_db(category, db, redis)


@router.put("/{id}",
            dependencies=[Depends(permission_required("can_update_category"))],
            response_model=CategoryRead)
async def update_category(id: str,
                          data: CategoryUpdate,
                          db: AsyncSession = Depends(get_db),
                          redis: Redis = Depends(get_redis)):
    return await update_category_in_db(id, data, db, redis)


@router.delete("/{id}",
               dependencies=[Depends(permission_required("can_delete_category"))],)
async def delete_category(id: str,
                          db: AsyncSession = Depends(get_db),
                          redis: Redis = Depends(get_redis)):
    return await delete_category_from_db(id, db, redis)
