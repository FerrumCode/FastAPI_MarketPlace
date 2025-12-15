from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from loguru import logger
from env import SERVICE_NAME

from app.models.product import Product
from app.db_depends import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.core.kafka import send_kafka_event
from app.crud.products import (
    get_all_products_from_db,
    create_product_in_db,
    update_product_in_db,
    get_product_from_db,
    delete_product_form_db,
)
from app.dependencies.depend import authentication_get_current_user, permission_required
from app.core.metrics import PRODUCTS_OPERATIONS_TOTAL


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductRead])
async def get_all_products(
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    operation = "list"
    logger.info("Request to GET all products")

    try:
        response = await get_all_products_from_db(db)
        logger.info(
            "Successfully retrieved products list, count={count}",
            count=len(response),
        )
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="success",
        ).inc()
        return response
    except Exception:
        logger.exception("Error while getting all products")
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="error",
        ).inc()
        raise


@router.get("/{id}", response_model=ProductRead)
async def get_product(
    id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    operation = "get"
    logger.info(
        "Request to GET product with id={id}",
        id=id,
    )

    try:
        response = await get_product_from_db(id, db)
        logger.info(
            "Product successfully retrieved: id={id}",
            id=id,
        )
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="success",
        ).inc()
        return response
    except Exception:
        logger.exception(
            "Error while getting product with id={id}",
            id=id,
        )
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="error",
        ).inc()
        raise


@router.post(
    "/",
    dependencies=[Depends(permission_required("can_create_product"))],
    response_model=ProductRead,
)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    operation = "create"
    logger.info(
        "Request to CREATE product with data={data}",
        data=data.dict(),
    )

    try:
        response = await create_product_in_db(data, db)
        logger.info(
            "Product successfully created: id={id}",
            id=response.id,
        )
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="success",
        ).inc()
        return response
    except Exception:
        logger.exception("Error while creating product")
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="error",
        ).inc()
        raise


@router.put(
    "/{id}",
    dependencies=[Depends(permission_required("can_update_product"))],
    response_model=ProductRead,
)
async def update_product(
    id: str,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    operation = "update"
    logger.info(
        "Request to UPDATE product with id={id}",
        id=id,
    )

    try:
        response = await update_product_in_db(id, data, db)
        logger.info(
            "Product successfully updated: id={id}",
            id=id,
        )
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="success",
        ).inc()
        return response
    except Exception:
        logger.exception(
            "Error while updating product with id={id}",
            id=id,
        )
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="error",
        ).inc()
        raise


@router.delete(
    "/{id}",
    dependencies=[Depends(permission_required("can_delete_product"))],
)
async def delete_product(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    operation = "delete"
    logger.info(
        "Request to DELETE product with id={id}",
        id=id,
    )

    try:
        response = await delete_product_form_db(id, db)
        logger.info(
            "Product with id={id} successfully deleted",
            id=id,
        )
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="success",
        ).inc()
        return response
    except Exception:
        logger.exception(
            "Error while deleting product with id={id}",
            id=id,
        )
        PRODUCTS_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation=operation,
            status="error",
        ).inc()
        raise
