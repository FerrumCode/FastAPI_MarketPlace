from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.product import Product
from app.db_depends import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.core.kafka import send_kafka_event


async def get_all_products_from_db(db: AsyncSession):
    logger.info("Request to get all products from DB")

    result = await db.execute(select(Product))
    products = result.scalars().all()

    logger.info(
        "Products list retrieved from DB, count={count}",
        count=len(products),
    )

    return [ProductRead.model_validate(p) for p in products]


async def get_product_from_db(id: str, db: AsyncSession):
    logger.info(
        "Request to get product from DB with id={id}",
        id=id,
    )

    result = await db.execute(select(Product).where(Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        logger.warning(
            "Product not found in DB with id={id}",
            id=id,
        )
        raise HTTPException(status_code=404, detail="Product not found")

    logger.info(
        "Product successfully retrieved from DB with id={id}",
        id=id,
    )

    return ProductRead.model_validate(product)


async def create_product_in_db(data: ProductCreate, db: AsyncSession):
    logger.info(
        "Attempt to create a new product with data={data}",
        data=data.dict(),
    )

    new_product = Product(**data.dict())
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    logger.info(
        "Product successfully created in DB: id={id}",
        id=new_product.id,
    )

    return ProductRead.model_validate(new_product)


async def update_product_in_db(id: str, data: ProductUpdate, db: AsyncSession):
    logger.info(
        "Attempt to update product with id={id}",
        id=id,
    )

    result = await db.execute(select(Product).where(Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        logger.warning(
            "Attempt to update non-existent product with id={id}",
            id=id,
        )
        raise HTTPException(status_code=404, detail="Product not found")

    logger.debug(
        "Applying updates to product id={id}: fields={fields}",
        id=id,
        fields=list(data.dict(exclude_unset=True).keys()),
    )

    for field, value in data.dict(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    logger.info(
        "Product successfully updated in DB: id={id}",
        id=id,
    )

    logger.info(
        "Sending Kafka event for updated product: id={id}",
        id=product.id,
    )

    await send_kafka_event("product_events", {
        "event": "PRODUCT_UPDATED",
        "product_id": str(product.id),
        "price": str(product.price),
    })

    logger.info(
        "Kafka event for product update sent successfully: product_id={id}",
        id=product.id,
    )

    return ProductRead.model_validate(product)


async def delete_product_form_db(id: str, db: AsyncSession):
    logger.info(
        "Attempt to delete product with id={id}",
        id=id,
    )

    result = await db.execute(select(Product).where(Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        logger.warning(
            "Attempt to delete non-existent product with id={id}",
            id=id,
        )
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()

    logger.info(
        "Product with id={id} successfully deleted from DB",
        id=id,
    )

    return {"detail": "Product deleted"}
