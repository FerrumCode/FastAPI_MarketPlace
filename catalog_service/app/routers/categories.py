from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio.client import Redis

from loguru import logger

from app.dependencies.depend import authentication_get_current_user, permission_required
from app.db_depends import get_db
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.core.redis import get_redis
from app.crud.categories import (
    get_all_categories_from_db,
    delete_category_from_db,
    create_category_in_db,
    update_category_in_db,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[CategoryRead])
async def get_all_categories(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user=Depends(authentication_get_current_user),
):
    logger.info("Request to GET all categories")

    try:
        response = await get_all_categories_from_db(db, redis)
        logger.info(
            "Successfully retrieved categories list, count={count}",
            count=len(response),
        )
        return response
    except Exception:
        logger.exception("Error while getting all categories")
        raise


@router.post(
    "/",
    dependencies=[Depends(permission_required("can_create_category"))],
    response_model=CategoryRead,
)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    logger.info(
        "Request to CREATE category with name='{name}'",
        name=category.name,
    )

    try:
        response = await create_category_in_db(category, db, redis)
        logger.info(
            "Category successfully created: id={id}, name='{name}'",
            id=response.id,
            name=response.name,
        )
        return response
    except Exception:
        logger.exception("Error while creating category")
        raise


@router.put(
    "/{id}",
    dependencies=[Depends(permission_required("can_update_category"))],
    response_model=CategoryRead,
)
async def update_category(
    id: str,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    logger.info(
        "Request to UPDATE category with id={id}",
        id=id,
    )

    try:
        response = await update_category_in_db(id, data, db, redis)
        logger.info(
            "Category successfully updated: id={id}, name='{name}'",
            id=response.id,
            name=response.name,
        )
        return response
    except Exception:
        logger.exception(
            "Error while updating category with id={id}",
            id=id,
        )
        raise


@router.delete(
    "/{id}",
    dependencies=[Depends(permission_required("can_delete_category"))],
)
async def delete_category(
    id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    logger.info(
        "Request to DELETE category with id={id}",
        id=id,
    )

    try:
        response = await delete_category_from_db(id, db, redis)
        logger.info(
            "Category with id={id} successfully deleted",
            id=id,
        )
        return response
    except Exception:
        logger.exception(
            "Error while deleting category with id={id}",
            id=id,
        )
        raise
