import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.category import Category
from app.db_depends import get_db
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.core.redis import get_redis

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[CategoryRead])
async def get_all_categories(db: AsyncSession = Depends(get_db)):
    redis = get_redis()
    cached = await redis.get("categories:list")
    if cached:
        return json.loads(cached)

    result = await db.execute(select(Category))
    categories = result.scalars().all()

    response = [CategoryRead.model_validate(c) for c in categories]
    await redis.set("categories:list", json.dumps([c.dict() for c in response]), ex=3600)
    return response


@router.post("/", response_model=CategoryRead)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    new_cat = Category(name=category.name)
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)

    redis = get_redis()
    await redis.delete("categories:list")  # сброс кеша
    return CategoryRead.model_validate(new_cat)


@router.put("/{id}", response_model=CategoryRead)
async def update_category(id: str, data: CategoryUpdate, db: AsyncSession = Depends(get_db)):
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


@router.delete("/{id}")
async def delete_category(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    await db.delete(cat)
    await db.commit()

    redis = get_redis()
    await redis.delete("categories:list")
    return {"detail": "Category deleted"}
