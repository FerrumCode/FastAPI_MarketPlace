from fastapi import APIRouter, Query, Depends, status, HTTPException
from app.schemas.review import ReviewCreate, ReviewOut, ReviewUpdate
from app.service import reviews as svc
from app.core.kafka import kafka_producer
from uuid import UUID
from app.service.reviews import get_review_by_id as svc_get_review_by_id

from app.dependencies.depend import (
    authentication_get_current_user,
    permission_required,
)
from loguru import logger

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
    logger.info(
        "Attempt to create review for product_id={product_id} by user_id={user_id}",
        product_id=payload.product_id,
        user_id=current_user["id"],
    )
    data = await svc.create_review(user_id=str(current_user["id"]), data=payload)
    logger.info(
        "Review created successfully: review_id={review_id}, product_id={product_id}, user_id={user_id}",
        review_id=data["id"],
        product_id=data["product_id"],
        user_id=data["user_id"],
    )

    try:
        logger.info(
            "Sending REVIEW_CREATED event to Kafka for review_id={review_id}, product_id={product_id}, user_id={user_id}",
            review_id=data["id"],
            product_id=data["product_id"],
            user_id=data["user_id"],
        )

        await kafka_producer.send_review_created(
            {
                "event": "REVIEW_CREATED",
                "product_id": data["product_id"],
                "user_id": data["user_id"],
                "rating": data["rating"],
                "text": data["text"],
                "review_id": data["id"],
            }
        )
        logger.info(
            "REVIEW_CREATED event successfully sent to Kafka for review_id={review_id}",
            review_id=data["id"],
        )
    except Exception as e:
        logger.warning("Kafka send failed: {error}", error=e)

    return data


@router.get("/{product_id}", response_model=list[ReviewOut])
async def get_reviews(
    product_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    logger.info(
        "Request to get reviews for product_id={product_id}, limit={limit}, offset={offset}",
        product_id=product_id,
        limit=limit,
        offset=offset,
    )
    data = await svc.get_reviews_for_product(
        product_id=product_id, limit=limit, offset=offset
    )
    logger.info(
        "Retrieved {count} review(s) for product_id={product_id}",
        count=len(data),
        product_id=product_id,
    )
    return data


@router.get("/by-id/{review_id}", response_model=ReviewOut)
async def get_review_by_id(review_id: str):
    logger.info(
        "Request to get review by id={review_id}",
        review_id=review_id,
    )
    data = await svc.get_review_by_id(review_id=review_id)
    logger.info(
        "Successfully retrieved review by id={review_id}",
        review_id=review_id,
    )
    return data


@router.patch(
    "/{review_id}",
    response_model=ReviewOut,
    dependencies=[Depends(permission_required("can_patch_review"))],
)
async def patch_review(
    review_id: str,
    payload: ReviewUpdate,
    current_user=Depends(authentication_get_current_user),
):
    logger.info(
        "Attempt to patch review_id={review_id} by user_id={user_id}",
        review_id=review_id,
        user_id=current_user["id"],
    )

    review = await svc_get_review_by_id(review_id)
    if not review:
        logger.warning(
            "Patch review: review_id={review_id} not found",
            review_id=review_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    review_user_uuid = UUID(review.get("user_id"))
    if review_user_uuid is None:
        logger.error(
            "Patch review: review_id={review_id} has no owner",
            review_id=review_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review has no owner",
        )

    current_user_uuid = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (review_user_uuid != current_user_uuid) and ("can_patch_all_reviews" not in perms):
        logger.warning(
            "Patch review forbidden for user_id={user_id} on review_id={review_id}",
            user_id=current_user["id"],
            review_id=review_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this review (owner only, role 'user')",
        )

    result = await svc.update_review(
        user_id=str(current_user["id"]),
        review_id=review_id,
        data=payload,
        can_update_others=True,
    )
    logger.info(
        "Review patched successfully: review_id={review_id} by user_id={user_id}",
        review_id=review_id,
        user_id=current_user["id"],
    )
    return result


@router.delete(
    "/{review_id}",
    dependencies=[Depends(permission_required("can_delete_review"))],
)
async def delete_review(
    review_id: str,
    current_user=Depends(authentication_get_current_user),
):
    logger.info(
        "Attempt to delete review_id={review_id} by user_id={user_id}",
        review_id=review_id,
        user_id=current_user["id"],
    )

    review = await svc_get_review_by_id(review_id)
    if not review:
        logger.warning(
            "Delete review: review_id={review_id} not found",
            review_id=review_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    review_user_uuid = UUID(review.get("user_id"))
    if review_user_uuid is None:
        logger.error(
            "Delete review: review_id={review_id} has no owner",
            review_id=review_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review has no owner",
        )

    current_user_uuid = UUID(current_user["id"])
    perms = current_user.get("permissions") or []
    if (review_user_uuid != current_user_uuid) and ("can_delete_all_reviews" not in perms):
        logger.warning(
            "Delete review forbidden for user_id={user_id} on review_id={review_id}",
            user_id=current_user["id"],
            review_id=review_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this review (owner only, role 'user')",
        )

    result = await svc.delete_review(
        user_id=str(current_user["id"]),
        review_id=review_id,
        can_delete_others=True,
    )
    logger.info(
        "Review deleted successfully: review_id={review_id} by user_id={user_id}",
        review_id=review_id,
        user_id=current_user["id"],
    )
    return result
