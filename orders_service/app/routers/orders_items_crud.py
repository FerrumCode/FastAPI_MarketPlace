from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from prometheus_client import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.order import Order

from app.db_depends import get_db
from app.schemas.order_item import OrderItemCreate, OrderItemRead, OrderItemUpdate
from app.crud.order_items import (
    get_order_item_from_db,
    create_order_item_in_db,
    update_order_item_in_db,
    delete_order_item_from_db,
)
from app.dependencies.depend import authentication_get_current_user, permission_required
from env import SERVICE_NAME

router = APIRouter(prefix="/order_items_crud", tags=["Order items CRUD"])

ORDER_ITEMS_API_REQUESTS_TOTAL = Counter(
    "order_items_api_requests_total",
    "Order items CRUD API request events",
    ["service", "endpoint", "method", "status"],
)


@router.get(
    "/{id}",
    response_model=OrderItemRead,
)
async def get_order_item(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authentication_get_current_user),
):
    ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/order_items_crud/{id}",
        method="GET",
        status="attempt",
    ).inc()
    logger.info(
        "Get order item request received. item_id='{item_id}', user_id='{user_id}'",
        item_id=id,
        user_id=current_user.get("id"),
    )
    order_item = await get_order_item_from_db(id, db)
    if not order_item:
        logger.warning(
            "Order item not found in get_order_item endpoint. item_id='{item_id}'",
            item_id=id,
        )
        ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/order_items_crud/{id}",
            method="GET",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    owner_id = await db.scalar(
        select(Order.user_id).where(Order.id == order_item.order_id)
    )
    if owner_id is None:
        logger.warning(
            "Order not found when checking owner for order item. item_id='{item_id}', order_id='{order_id}'",
            item_id=id,
            order_id=str(order_item.order_id),
        )
        ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/order_items_crud/{id}",
            method="GET",
            status="order_not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_id = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (owner_id != user_id) and ("can_get_all_order_items" not in perms):
        logger.warning(
            "Access to order item forbidden in get_order_item. item_id='{item_id}', user_id='{user_id}'",
            item_id=id,
            user_id=str(user_id),
        )
        ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/order_items_crud/{id}",
            method="GET",
            status="forbidden",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )
    logger.info(
        "Order item successfully returned in get_order_item. item_id='{item_id}', user_id='{user_id}'",
        item_id=id,
        user_id=str(user_id),
    )
    ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/order_items_crud/{id}",
        method="GET",
        status="success",
    ).inc()
    return order_item


@router.post(
    "/",
    dependencies=[Depends(permission_required("can_create_order_item"))],
    response_model=OrderItemRead,
)
async def create_order_item(
    data: OrderItemCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(authentication_get_current_user),
):
    ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/order_items_crud/",
        method="POST",
        status="attempt",
    ).inc()
    logger.info(
        "Create order item request received. order_id='{order_id}', user_id='{user_id}'",
        order_id=str(data.order_id),
        user_id=user.get("id"),
    )
    result = await create_order_item_in_db(data, db)
    logger.info(
        "Order item created successfully in create_order_item endpoint. item_id='{item_id}', order_id='{order_id}'",
        item_id=str(result.id),
        order_id=str(result.order_id),
    )
    ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/order_items_crud/",
        method="POST",
        status="success",
    ).inc()
    return result


@router.put(
    "/{id}",
    dependencies=[Depends(permission_required("can_update_order_item"))],
    response_model=OrderItemRead,
)
async def update_order_item(
    id: str,
    data: OrderItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authentication_get_current_user),
):
    ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/order_items_crud/{id}",
        method="PUT",
        status="attempt",
    ).inc()
    logger.info(
        "Update order item request received. item_id='{item_id}', user_id='{user_id}'",
        item_id=id,
        user_id=current_user.get("id"),
    )
    order_item = await get_order_item_from_db(id, db)
    if not order_item:
        logger.warning(
            "Order item not found in update_order_item endpoint. item_id='{item_id}'",
            item_id=id,
        )
        ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/order_items_crud/{id}",
            method="PUT",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    owner_id = await db.scalar(
        select(Order.user_id).where(Order.id == order_item.order_id)
    )
    if owner_id is None:
        logger.warning(
            "Order not found when checking owner for update in update_order_item. item_id='{item_id}', order_id='{order_id}'",
            item_id=id,
            order_id=str(order_item.order_id),
        )
        ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/order_items_crud/{id}",
            method="PUT",
            status="order_not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_id = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (owner_id != user_id) and ("can_update_all_order_items" not in perms):
        logger.warning(
            "Access to order item forbidden in update_order_item. item_id='{item_id}', user_id='{user_id}'",
            item_id=id,
            user_id=str(user_id),
        )
        ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/order_items_crud/{id}",
            method="PUT",
            status="forbidden",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )
    result = await update_order_item_in_db(id, data, db)
    logger.info(
        "Order item updated successfully in update_order_item endpoint. item_id='{item_id}', order_id='{order_id}'",
        item_id=id,
        order_id=str(result.order_id),
    )
    ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/order_items_crud/{id}",
        method="PUT",
        status="success",
    ).inc()
    return result


@router.delete(
    "/{id}",
    dependencies=[Depends(permission_required("can_delete_order_item"))],
)
async def delete_order_item(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authentication_get_current_user),
):
    ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/order_items_crud/{id}",
        method="DELETE",
        status="attempt",
    ).inc()
    logger.info(
        "Delete order item request received. item_id='{item_id}', user_id='{user_id}'",
        item_id=id,
        user_id=current_user.get("id"),
    )
    order_item = await get_order_item_from_db(id, db)
    if not order_item:
        logger.warning(
            "Order item not found in delete_order_item endpoint. item_id='{item_id}'",
            item_id=id,
        )
        ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/order_items_crud/{id}",
            method="DELETE",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    owner_id = await db.scalar(
        select(Order.user_id).where(Order.id == order_item.order_id)
    )
    if owner_id is None:
        logger.warning(
            "Order not found when checking owner for delete in delete_order_item. item_id='{item_id}', order_id='{order_id}'",
            item_id=id,
            order_id=str(order_item.order_id),
        )
        ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/order_items_crud/{id}",
            method="DELETE",
            status="order_not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_id = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (owner_id != user_id) and ("can_delete_all_order_items" not in perms):
        logger.warning(
            "Access to order item forbidden in delete_order_item. item_id='{item_id}', user_id='{user_id}'",
            item_id=id,
            user_id=str(user_id),
        )
        ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/order_items_crud/{id}",
            method="DELETE",
            status="forbidden",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )
    result = await delete_order_item_from_db(id, db)
    logger.info(
        "Order item deleted successfully in delete_order_item endpoint. item_id='{item_id}'",
        item_id=id,
    )
    ORDER_ITEMS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/order_items_crud/{id}",
        method="DELETE",
        status="success",
    ).inc()
    return result
