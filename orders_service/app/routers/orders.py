from uuid import UUID
from typing import Any, Dict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from loguru import logger
from prometheus_client import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.kafka import kafka_producer
from app.db_depends import get_db
from app.dependencies.depend import (
    authentication_get_current_user,
    permission_required,
    bearer_scheme,
)
from app.models.order import Order
from app.schemas.order import (
    OrderCreate,
    OrderOut,
    OrderStatusPatch,
    FinalOrderPatch,
)
from app.service.orders import (
    create_order as svc_create_order,
    get_order as svc_get_order,
    delete_order as svc_delete_order,
    update_order_status as svc_update_order_status,
)
from env import KAFKA_ORDER_TOPIC, CURRENCY_BASE, SERVICE_NAME

router = APIRouter(prefix="/orders", tags=["Orders"])

ORDERS_API_REQUESTS_TOTAL = Counter(
    "orders_orders_api_requests_total",
    "Orders API request events",
    ["service", "endpoint", "method", "status"],
)


@router.post(
    "/",
    dependencies=[Depends(permission_required("can_create_order"))],
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authentication_get_current_user),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    logger.info(
        "Create order request received for user_id='{user_id}'",
        user_id=current_user.get("id"),
    )
    bearer_header = f"Bearer {creds.credentials}"

    user_uuid = (
        current_user["id"]
        if isinstance(current_user["id"], UUID)
        else UUID(str(current_user["id"]))
    )

    async with db.begin():
        created_order = await svc_create_order(
            db,
            user_id=user_uuid,
            items_in=[item.model_dump() for item in payload.items],
            currency_base=CURRENCY_BASE,
            target_currency=payload.target_currency,
            auth_header=bearer_header,
        )

    logger.info(
        "Order created via service. order_id='{order_id}', user_id='{user_id}'",
        order_id=str(created_order.id),
        user_id=str(user_uuid),
    )

    order_full = await svc_get_order(db, created_order.id)
    if not order_full:
        logger.error(
            "Order lost after creation. order_id='{order_id}'",
            order_id=str(created_order.id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/",
            method="POST",
            status="order_lost",
        ).inc()
        raise HTTPException(status_code=500, detail="Order lost after creation")

    await kafka_producer.send(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_CREATED",
            "order_id": str(order_full.id),
            "user_id": str(order_full.user_id),
            "target_currency": payload.target_currency,
            "currency_base": CURRENCY_BASE,
            "items": [
                {
                    "product_id": str(i.product_id),
                    "quantity": i.quantity,
                    "unit_price": float(i.unit_price),
                }
                for i in order_full.items
            ],
            "cart_price": float(order_full.cart_price),
            "delivery_price": float(order_full.delivery_price),
            "total_price": float(order_full.total_price),
            "status": order_full.status,
        },
        key=str(order_full.id),
    )
    logger.info(
        "Kafka event 'ORDER_CREATED' sent from orders router. order_id='{order_id}'",
        order_id=str(order_full.id),
    )

    ORDERS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/orders/",
        method="POST",
        status="success",
    ).inc()
    return order_full


@router.get(
    "/{order_id}",
    dependencies=[Depends(permission_required("can_get_order"))],
    response_model=OrderOut,
)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authentication_get_current_user),
):
    logger.info(
        "Get order request received. order_id='{order_id}', user_id='{user_id}'",
        order_id=str(order_id),
        user_id=current_user.get("id"),
    )
    order = await svc_get_order(db, order_id)
    if not order:
        logger.warning(
            "Order not found in get_order endpoint. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/{order_id}",
            method="GET",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_id = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (order.user_id != user_id) and ("can_get_all_orders" not in perms):
        logger.warning(
            "Access to order forbidden in get_order endpoint. order_id='{order_id}', user_id='{user_id}'",
            order_id=str(order_id),
            user_id=str(user_id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/{order_id}",
            method="GET",
            status="forbidden",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )

    logger.info(
        "Order successfully returned in get_order endpoint. order_id='{order_id}', user_id='{user_id}'",
        order_id=str(order_id),
        user_id=str(user_id),
    )
    ORDERS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/orders/{order_id}",
        method="GET",
        status="success",
    ).inc()
    return order


@router.delete(
    "/{order_id}",
    dependencies=[Depends(permission_required("can_delete_order"))],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authentication_get_current_user),
):
    logger.info(
        "Delete order request received. order_id='{order_id}', user_id='{user_id}'",
        order_id=str(order_id),
        user_id=current_user.get("id"),
    )
    order = await svc_get_order(db, order_id)
    if not order:
        logger.warning(
            "Order not found in delete_order endpoint. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/{order_id}",
            method="DELETE",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_id = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (order.user_id != user_id) and ("can_delete_all_orders" not in perms):
        logger.warning(
            "Access to order forbidden in delete_order endpoint. order_id='{order_id}', user_id='{user_id}'",
            order_id=str(order_id),
            user_id=str(user_id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/{order_id}",
            method="DELETE",
            status="forbidden",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )

    async with db.begin():
        await svc_delete_order(db, order_id)

    await kafka_producer.send(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_UPDATED",
            "order_id": str(order_id),
            "status": "deleted",
        },
        key=str(order_id),
    )
    logger.info(
        "Kafka event 'ORDER_UPDATED' sent from delete_order endpoint. order_id='{order_id}'",
        order_id=str(order_id),
    )

    ORDERS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/orders/{order_id}",
        method="DELETE",
        status="success",
    ).inc()
    return None


@router.patch(
    "/{order_id}",
    dependencies=[Depends(permission_required("can_patch_order_status"))],
    response_model=OrderOut,
)
async def patch_order_status(
    order_id: UUID,
    payload: OrderStatusPatch,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authentication_get_current_user),
):
    logger.info(
        "Patch order status request received. order_id='{order_id}', new_status='{status}', user_id='{user_id}'",
        order_id=str(order_id),
        status=payload.status,
        user_id=current_user.get("id"),
    )
    order = await svc_get_order(db, order_id)
    if not order:
        logger.warning(
            "Order not found in patch_order_status endpoint. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/{order_id}",
            method="PATCH",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_id = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (order.user_id != user_id) and ("can_patch_all_orders_status" not in perms):
        logger.warning(
            "Access to order forbidden in patch_order_status endpoint. order_id='{order_id}', user_id='{user_id}'",
            order_id=str(order_id),
            user_id=str(user_id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/{order_id}",
            method="PATCH",
            status="forbidden",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )

    async with db.begin():
        await svc_update_order_status(db, order_id, payload.status)

    await kafka_producer.send(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_UPDATED",
            "order_id": str(order_id),
            "status": payload.status,
        },
        key=str(order_id),
    )
    logger.info(
        "Kafka event 'ORDER_UPDATED' sent from patch_order_status endpoint. order_id='{order_id}', status='{status}'",
        order_id=str(order_id),
        status=payload.status,
    )

    fresh = await svc_get_order(db, order_id)
    if not fresh:
        logger.error(
            "Order not found after status patch in patch_order_status endpoint. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/{order_id}",
            method="PATCH",
            status="not_found_after_patch",
        ).inc()
        raise HTTPException(status_code=404, detail="Order not found")

    logger.info(
        "Order successfully updated in patch_order_status endpoint. order_id='{order_id}', status='{status}'",
        order_id=str(order_id),
        status=fresh.status,
    )
    ORDERS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/orders/{order_id}",
        method="PATCH",
        status="success",
    ).inc()
    return fresh


@router.patch(
    "/make_final_order_with_delivery/{order_id}",
    dependencies=[Depends(permission_required("can_patch_order_status"))],
    response_model=OrderOut,
)
async def make_final_order_with_delivery(
    order_id: UUID,
    payload: FinalOrderPatch,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authentication_get_current_user),
):
    logger.info(
        "Finalizing order with delivery request received. order_id='{order_id}', user_id='{user_id}'",
        order_id=str(order_id),
        user_id=current_user.get("id"),
    )
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        logger.warning(
            "Order not found in make_final_order_with_delivery endpoint. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/make_final_order_with_delivery/{order_id}",
            method="PATCH",
            status="not_found",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if payload.items:
        items_by_id = {item.id: item for item in order.items}
        items_by_product = {item.product_id: item for item in order.items}

        for patch_item in payload.items:
            target_item = None
            if patch_item.id is not None:
                target_item = items_by_id.get(patch_item.id)
            elif patch_item.product_id is not None:
                target_item = items_by_product.get(patch_item.product_id)

            if target_item is None:
                logger.warning(
                    "Order item for update not found in make_final_order_with_delivery. order_id='{order_id}'",
                    order_id=str(order_id),
                )
                ORDERS_API_REQUESTS_TOTAL.labels(
                    service=SERVICE_NAME,
                    endpoint="/orders/make_final_order_with_delivery/{order_id}",
                    method="PATCH",
                    status="item_not_found",
                ).inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order item for update not found",
                )

            if patch_item.quantity is not None:
                logger.debug(
                    "Updating quantity for item in finalized order. order_id='{order_id}', item_id='{item_id}', quantity={quantity}",
                    order_id=str(order_id),
                    item_id=str(target_item.id),
                    quantity=patch_item.quantity,
                )
                target_item.quantity = patch_item.quantity
            if patch_item.unit_price is not None:
                logger.debug(
                    "Updating unit_price for item in finalized order. order_id='{order_id}', item_id='{item_id}', unit_price={unit_price}",
                    order_id=str(order_id),
                    item_id=str(target_item.id),
                    unit_price=patch_item.unit_price,
                )
                target_item.unit_price = patch_item.unit_price

    if payload.cart_price is not None:
        logger.debug(
            "Overriding cart_price for finalized order. order_id='{order_id}', cart_price={cart_price}",
            order_id=str(order_id),
            cart_price=payload.cart_price,
        )
        order.cart_price = payload.cart_price
    elif payload.items:
        cart = Decimal("0.00")
        for item in order.items:
            cart += Decimal(str(item.unit_price)) * int(item.quantity)
        logger.debug(
            "Recalculated cart_price for finalized order. order_id='{order_id}', cart_price={cart_price}",
            order_id=str(order_id),
            cart_price=float(cart),
        )
        order.cart_price = cart

    if payload.delivery_price is not None:
        logger.debug(
            "Setting delivery_price for finalized order. order_id='{order_id}', delivery_price={delivery_price}",
            order_id=str(order_id),
            delivery_price=payload.delivery_price,
        )
        order.delivery_price = payload.delivery_price

    if payload.total_price is not None:
        logger.debug(
            "Overriding total_price for finalized order. order_id='{order_id}', total_price={total_price}",
            order_id=str(order_id),
            total_price=payload.total_price,
        )
        order.total_price = payload.total_price
    else:
        if payload.cart_price is not None or payload.delivery_price is not None or payload.items:
            order.total_price = order.cart_price + order.delivery_price
            logger.debug(
                "Recalculated total_price for finalized order. order_id='{order_id}', total_price={total_price}",
                order_id=str(order_id),
                total_price=float(order.total_price),
            )

    if payload.status is not None:
        logger.debug(
            "Setting status for finalized order. order_id='{order_id}', status='{status}'",
            order_id=str(order_id),
            status=payload.status,
        )
        order.status = payload.status

    await db.commit()
    logger.info(
        "Order finalized with delivery and committed to DB. order_id='{order_id}'",
        order_id=str(order_id),
    )

    result2 = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    fresh = result2.scalar_one_or_none()
    if not fresh:
        logger.error(
            "Order not found after finalization in make_final_order_with_delivery. order_id='{order_id}'",
            order_id=str(order_id),
        )
        ORDERS_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            endpoint="/orders/make_final_order_with_delivery/{order_id}",
            method="PATCH",
            status="not_found_after_finalize",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    await kafka_producer.send(
        KAFKA_ORDER_TOPIC,
        {
            "event": "ORDER_UPDATED",
            "order_id": str(fresh.id),
            "user_id": str(fresh.user_id),
            "status": fresh.status,
            "cart_price": float(fresh.cart_price),
            "delivery_price": float(fresh.delivery_price),
            "total_price": float(fresh.total_price),
            "items": [
                {
                    "product_id": str(i.product_id),
                    "quantity": i.quantity,
                    "unit_price": float(i.unit_price),
                }
                for i in fresh.items
            ],
            "reason": "finalized_with_delivery",
        },
        key=str(fresh.id),
    )
    logger.info(
        "Kafka event 'ORDER_UPDATED' sent from make_final_order_with_delivery endpoint. order_id='{order_id}'",
        order_id=str(fresh.id),
    )

    ORDERS_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        endpoint="/orders/make_final_order_with_delivery/{order_id}",
        method="PATCH",
        status="success",
    ).inc()
    return OrderOut.model_validate(fresh)
