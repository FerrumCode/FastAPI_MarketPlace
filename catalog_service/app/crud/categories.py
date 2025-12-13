import json
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio.client import Redis
from loguru import logger

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate


async def get_all_categories_from_db(db: AsyncSession, redis: Redis):
    logger.info("Request to get all categories (try Redis cache first)")

    cached = await redis.get("categories:list")
    if cached:
        logger.info("Categories list retrieved from Redis cache")
        return json.loads(cached)

    logger.info("Categories not found in cache, querying DB for all categories")

    result = await db.execute(select(Category))
    categories = result.scalars().all()

    response = [CategoryRead.model_validate(c) for c in categories]

    logger.info(
        "Categories list retrieved from DB and will be cached, count={count}",
        count=len(response),
    )

    await redis.set(
        "categories:list",
        json.dumps([c.dict() for c in response], default=str),
        ex=3600
    )

    return response


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

    await redis.delete("categories:list")
    logger.debug("Categories cache invalidated after category creation")

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

    logger.debug(
        "Applying updates to category id={id}: fields={fields}",
        id=id,
        fields=list(data.dict(exclude_unset=True).keys()),
    )

    for field, value in data.dict(exclude_unset=True).items():
        setattr(cat, field, value)

    await db.commit()
    await db.refresh(cat)

    logger.info(
        "Category successfully updated in DB: id={id}",
        id=id,
    )

    await redis.delete("categories:list")
    logger.debug("Categories cache invalidated after category update")

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

    await redis.delete("categories:list")
    logger.debug("Categories cache invalidated after category deletion")

    return {"detail": "Category deleted"}
