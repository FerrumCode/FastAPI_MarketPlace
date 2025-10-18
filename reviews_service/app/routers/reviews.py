import logging
from fastapi import APIRouter, Query
from app.dependencies.auth import CurrentUser, require_role
from app.schemas.review import ReviewCreate, ReviewOut, ReviewUpdate
from app.service import reviews as svc
from app.core.kafka import kafka_producer


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/", response_model=ReviewOut, status_code=201)
async def add_review(payload: ReviewCreate, user: CurrentUser = None):
    data = await svc.create_review(user_id=user.id, data=payload)
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


@router.get("/{product_id}", response_model=list[ReviewOut])
async def get_reviews(product_id: str, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return await svc.get_reviews_for_product(product_id=product_id, limit=limit, offset=offset)


@router.patch("/{product_id}", response_model=ReviewOut)
async def patch_review(product_id: str, payload: ReviewUpdate, user: CurrentUser = None):
    can = user.role in ("admin", "manager")
    return await svc.update_review(user_id=user.id, product_id=product_id, data=payload, can_update_others=can)


@router.delete("/{product_id}")
async def delete_review(product_id: str, user: CurrentUser = None):
    can = user.role in ("admin", "manager")
    return await svc.delete_review(user_id=user.id, product_id=product_id, can_delete_others=can)
