from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger

from app.db_depends import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.crud.products import (
    get_all_products_from_db,
    create_product_in_db,
    update_product_in_db,
    get_product_from_db,
    delete_product_form_db,
)
from app.dependencies.depend import authentication_get_current_user, permission_required

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductRead])
async def get_all_products(
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    logger.info("Request to GET all products")

    try:
        response = await get_all_products_from_db(db)
        logger.info(
            "Successfully retrieved products list, count={count}",
            count=len(response),
        )
        return response
    except Exception:
        logger.exception("Error while getting all products")
        raise


@router.get("/{id}", response_model=ProductRead)
async def get_product(
    id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
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
        return response
    except Exception:
        logger.exception(
            "Error while getting product with id={id}",
            id=id,
        )
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
        return response
    except Exception:
        logger.exception("Error while creating product")
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
        return response
    except Exception:
        logger.exception(
            "Error while updating product with id={id}",
            id=id,
        )
        raise


@router.delete(
    "/{id}",
    dependencies=[Depends(permission_required("can_delete_product"))],
)
async def delete_product(
    id: str,
    db: AsyncSession = Depends(get_db),
):
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
        return response
    except Exception:
        logger.exception(
            "Error while deleting product with id={id}",
            id=id,
        )
        raise
