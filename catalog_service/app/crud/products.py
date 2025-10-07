from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product
from app.db_depends import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.core.kafka import send_kafka_event



async def get_all_products_from_db(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product))
    products = result.scalars().all()
    return [ProductRead.model_validate(p) for p in products]


async def get_product_from_db(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductRead.model_validate(product)


async def create_product_in_db(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    new_product = Product(**data.dict())
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return ProductRead.model_validate(new_product)


async def update_product_in_db(id: str, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    # отправляем событие в Kafka
    await send_kafka_event("product_events", {
        "event": "PRODUCT_UPDATED",
        "product_id": str(product.id),
        "price": str(product.price),
    })

    return ProductRead.model_validate(product)


async def delete_product_form_db(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
    return {"detail": "Product deleted"}