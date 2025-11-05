from fastapi import APIRouter, Query, Depends, status
from app.schemas.review import ReviewCreate, ReviewOut, ReviewUpdate
from app.service import reviews as svc
from app.core.kafka import kafka_producer

from app.dependencies.depend import (
    authentication_get_current_user,
    permission_required,
    user_owner_access_checker,
)

import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post(
    "/",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(permission_required("can_add_review"))],
)
async def add_review(
    payload: ReviewCreate,
    current_user=Depends(authentication_get_current_user),
):
    data = await svc.create_review(user_id=str(current_user["id"]), data=payload)

    # Отправляем событие в Kafka (не критично)
    try:
        await kafka_producer.send_review_created({
            "event": "REVIEW_CREATED",
            "product_id": data["product_id"],
            "user_id": data["user_id"],
            "rating": data["rating"],
            "text": data["text"],
            "review_id": data["id"],
        })
    except Exception as e:
        logger.warning("Kafka send failed: %s", e)
    return data


@router.get("/", response_model=list[ReviewOut])
async def get_all_reviews(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await svc.get_all_reviews(limit=limit, offset=offset)


@router.get("/{product_id}", response_model=list[ReviewOut])
async def get_reviews(
    product_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    return await svc.get_reviews_for_product(product_id=product_id, limit=limit, offset=offset)


@router.get("/by-id/{review_id}", response_model=ReviewOut)
async def get_review_by_id(review_id: str):
    return await svc.get_review_by_id(review_id=review_id)


@router.patch(
    "/{review_id}",
    response_model=ReviewOut,
    dependencies=[Depends(permission_required("can_patch_review"))],
)
async def patch_review(
    review_id: str,
    payload: ReviewUpdate,
    current_user=Depends(authentication_get_current_user),
    _: None = Depends(user_owner_access_checker),
):
    # can_update_others ставим True — доступ для чужих отзывов уже отсечён зависимостью user_owner_access_checker
    return await svc.update_review(
        user_id=str(current_user["id"]),
        review_id=review_id,
        data=payload,
        can_update_others=True,
    )


@router.delete(
    "/{review_id}",
    dependencies=[Depends(permission_required("can_delete_review"))],
)
async def delete_review(
    review_id: str,
    current_user=Depends(authentication_get_current_user),
    _: None = Depends(user_owner_access_checker),
):
    # can_delete_others ставим True — доступ для чужих отзывов уже отсечён зависимостью user_owner_access_checker
    return await svc.delete_review(
        user_id=str(current_user["id"]),
        review_id=review_id,
        can_delete_others=True,
    )
