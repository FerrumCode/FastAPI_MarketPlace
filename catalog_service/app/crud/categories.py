import json
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio.client import Redis
from loguru import logger

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.core.metrics import (
    REDIS_OPS,
    REDIS_CACHE_HITS_TOTAL,
    REDIS_CACHE_MISSES_TOTAL,
)
from env import SERVICE_NAME, CATEGORIES_CACHE_KEY, CATEGORIES_CACHE_TTL_SECONDS


async def get_all_categories_from_db(db: AsyncSession, redis: Redis):
    logger.info("Request to get all categories (try Redis cache first)")

    try:
        cached = await redis.get(CATEGORIES_CACHE_KEY)
        REDIS_OPS.labels(service=SERVICE_NAME, operation="get", status="success").inc()
    except Exception:
        REDIS_OPS.labels(service=SERVICE_NAME, operation="get", status="error").inc()
        logger.exception("Redis GET failed for key={key}", key=CATEGORIES_CACHE_KEY)
        raise

    if cached is not None:
        REDIS_CACHE_HITS_TOTAL.labels(service=SERVICE_NAME, cache_key=CATEGORIES_CACHE_KEY).inc()
        logger.info("Categories list retrieved from Redis cache")
        return json.loads(cached)

    REDIS_CACHE_MISSES_TOTAL.labels(service=SERVICE_NAME, cache_key=CATEGORIES_CACHE_KEY).inc()
    logger.info("Categories not found in cache, querying DB for all categories")

    result = await db.execute(select(Category))
    categories = result.scalars().all()

    response_models = [CategoryRead.model_validate(c) for c in categories]

    logger.info(
        "Categories list retrieved from DB and will be cached, count={count}",
        count=len(response_models),
    )

    payload = json.dumps([c.model_dump() for c in response_models], default=str)

    try:
        await redis.set(CATEGORIES_CACHE_KEY, payload, ex=CATEGORIES_CACHE_TTL_SECONDS)
        REDIS_OPS.labels(service=SERVICE_NAME, operation="set", status="success").inc()
    except Exception:
        REDIS_OPS.labels(service=SERVICE_NAME, operation="set", status="error").inc()
        logger.exception("Redis SET failed for key={key}", key=CATEGORIES_CACHE_KEY)
        raise

    return response_models


async def create_category_in_db(category: CategoryCreate, db: AsyncSession, redis: Redis):
    logger.info(
        "Attempt to create a new category with name='{name}'",
        name=category.name,
    )

    new_cat = Category(name=category.name)
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)

    logger.info(
        "Category successfully created in DB: id={id}, name='{name}'",
        id=new_cat.id,
        name=new_cat.name,
    )

    try:
        deleted = await redis.delete(CATEGORIES_CACHE_KEY)  # 0 или 1
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="delete",
            status="success" if deleted else "noop",
        ).inc()
        logger.debug("Categories cache invalidated after category creation (deleted={d})", d=deleted)
    except Exception:
        REDIS_OPS.labels(service=SERVICE_NAME, operation="delete", status="error").inc()
        logger.exception("Redis DELETE failed for key={key}", key=CATEGORIES_CACHE_KEY)
        raise

    return CategoryRead.model_validate(new_cat)


async def update_category_in_db(id: str, data: CategoryUpdate, db: AsyncSession, redis: Redis):
    logger.info(
        "Attempt to update category with id={id}",
        id=id,
    )

    result = await db.execute(select(Category).where(Category.id == id))
    cat = result.scalar_one_or_none()
    if not cat:
        logger.warning(
            "Attempt to update non-existent category with id={id}",
            id=id,
        )
        raise HTTPException(status_code=404, detail="Category not found")

    updates = data.model_dump(exclude_unset=True)
    logger.debug(
        "Applying updates to category id={id}: fields={fields}",
        id=id,
        fields=list(updates.keys()),
    )

    for field, value in updates.items():
        setattr(cat, field, value)

    await db.commit()
    await db.refresh(cat)

    logger.info(
        "Category successfully updated in DB: id={id}",
        id=id,
    )

    try:
        deleted = await redis.delete(CATEGORIES_CACHE_KEY)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="delete",
            status="success" if deleted else "noop",
        ).inc()
        logger.debug("Categories cache invalidated after category update (deleted={d})", d=deleted)
    except Exception:
        REDIS_OPS.labels(service=SERVICE_NAME, operation="delete", status="error").inc()
        logger.exception("Redis DELETE failed for key={key}", key=CATEGORIES_CACHE_KEY)
        raise

    return CategoryRead.model_validate(cat)


async def delete_category_from_db(id: str, db: AsyncSession, redis: Redis):
    logger.info(
        "Attempt to delete category with id={id}",
        id=id,
    )

    result = await db.execute(select(Category).where(Category.id == id))
    cat = result.scalar_one_or_none()
    if not cat:
        logger.warning(
            "Attempt to delete non-existent category with id={id}",
            id=id,
        )
        raise HTTPException(status_code=404, detail="Category not found")

    await db.delete(cat)
    await db.commit()

    logger.info(
        "Category with id={id} successfully deleted from DB",
        id=id,
    )

    try:
        deleted = await redis.delete(CATEGORIES_CACHE_KEY)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="delete",
            status="success" if deleted else "noop",
        ).inc()
        logger.debug("Categories cache invalidated after category deletion (deleted={d})", d=deleted)
    except Exception:
        REDIS_OPS.labels(service=SERVICE_NAME, operation="delete", status="error").inc()
        logger.exception("Redis DELETE failed for key={key}", key=CATEGORIES_CACHE_KEY)
        raise

    return {"detail": "Category deleted"}
