import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.category import Category
from app.db_depends import get_db
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.core.redis import get_redis



async def get_all_categories_from_db(db: AsyncSession = Depends(get_db)):
    redis = get_redis()

    cached = await redis.get("categories:list")
    if cached:
        return json.loads(cached)

    result = await db.execute(select(Category))
    categories = result.scalars().all()

    response = [CategoryRead.model_validate(c) for c in categories]

    await redis.set(
        "categories:list",
        json.dumps([c.dict() for c in response], default=str),
        ex=3600
    )

    return response


async def create_category_in_db(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    new_cat = Category(name=category.name)
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)

    redis = get_redis()
    await redis.delete("categories:list")  # сброс кеша
    return CategoryRead.model_validate(new_cat)


async def update_category_in_db(id: str, data: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(cat, field, value)

    await db.commit()
    await db.refresh(cat)

    redis = get_redis()
    await redis.delete("categories:list")
    return CategoryRead.model_validate(cat)


async def delete_category_from_db(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    await db.delete(cat)
    await db.commit()

    redis = get_redis()
    await redis.delete("categories:list")
    return {"detail": "Category deleted"}