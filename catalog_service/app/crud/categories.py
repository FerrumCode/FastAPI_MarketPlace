import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio.client import Redis

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate



async def get_category_by_id_or_name(
    db: AsyncSession,
    redis: Redis,
    id: Optional[str] = None,
    name: Optional[str] = None,
) -> CategoryRead:
    if (id is None and name is None) or (id is not None and name is not None):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of the query params: 'id' or 'name'.",
        )

    if id is not None:
        cache_key = f"category:id:{id}"
        cached = await redis.get(cache_key)
        if cached:
            return CategoryRead.model_validate(json.loads(cached))

        result = await db.execute(select(Category).where(Category.id == id))
        cat = result.scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")

        response = CategoryRead.model_validate(cat)
        await redis.set(cache_key, json.dumps(response.dict(), default=str), ex=3600)
        return response

    cache_key = f"category:name:{name}"
    cached = await redis.get(cache_key)
    if cached:
        return CategoryRead.model_validate(json.loads(cached))

    result = await db.execute(
        select(Category).where(Category.name == name).limit(1)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    response = CategoryRead.model_validate(cat)
    await redis.set(cache_key, json.dumps(response.dict(), default=str), ex=3600)
    return response


async def create_category_in_db(
    category: CategoryCreate, db: AsyncSession, redis: Redis
):
    new_cat = Category(name=category.name)
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)

    await redis.delete("categories:list")
    await redis.delete(f"category:id:{new_cat.id}")
    await redis.delete(f"category:name:{new_cat.name}")

    return CategoryRead.model_validate(new_cat)


async def update_category_in_db(
    id: str, data: CategoryUpdate, db: AsyncSession, redis: Redis
):
    result = await db.execute(select(Category).where(Category.id == id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    old_name = cat.name

    for field, value in data.dict(exclude_unset=True).items():
        setattr(cat, field, value)

    await db.commit()
    await db.refresh(cat)

    await redis.delete("categories:list")
    await redis.delete(f"category:id:{cat.id}")
    await redis.delete(f"category:name:{old_name}")
    await redis.delete(f"category:name:{cat.name}")

    return CategoryRead.model_validate(cat)


async def delete_category_from_db(id: str, db: AsyncSession, redis: Redis):
    result = await db.execute(select(Category).where(Category.id == id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    del_name = cat.name
    del_id = cat.id

    await db.delete(cat)
    await db.commit()

    await redis.delete("categories:list")
    await redis.delete(f"category:id:{del_id}")
    await redis.delete(f"category:name:{del_name}")

    return {"detail": "Category deleted"}
