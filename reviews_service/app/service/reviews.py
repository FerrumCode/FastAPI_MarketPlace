from datetime import datetime
from typing import Any, Mapping

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from bson.errors import InvalidId

from app.db import get_reviews_col
from app.schemas.review import ReviewCreate, ReviewUpdate
from loguru import logger
from prometheus_client import Counter
from env import SERVICE_NAME


REVIEWS_DB_REQUESTS_TOTAL = Counter(
    "reviews_db_requests_total",
    "Total DB requests for reviews (used to calculate RPS/RPM)",
    ["service"],
)


def _now() -> datetime:
    return datetime.utcnow()


def _oid(review_id: str) -> ObjectId:
    try:
        return ObjectId(review_id)
    except (InvalidId, TypeError):
        logger.warning(
            "Invalid review id '{review_id}' passed to _oid helper",
            review_id=review_id,
        )
        raise HTTPException(status_code=400, detail="Invalid review id")


def serialize(doc: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "product_id": doc["product_id"],
        "user_id": doc["user_id"],
        "rating": doc["rating"],
        "text": doc.get("text", ""),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


async def create_review(user_id: str, data: ReviewCreate) -> dict:
    REVIEWS_DB_REQUESTS_TOTAL.labels(service=SERVICE_NAME).inc()

    col = get_reviews_col()
    doc = {
        "product_id": data.product_id,
        "user_id": user_id,
        "rating": data.rating,
        "text": data.text or "",
        "created_at": _now(),
        "updated_at": _now(),
    }
    logger.info(
        "Attempt to create review in DB for product_id={product_id}, user_id={user_id}",
        product_id=data.product_id,
        user_id=user_id,
    )
    try:
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        logger.info(
            "Review created in DB with id={review_id} for product_id={product_id}, user_id={user_id}",
            review_id=str(res.inserted_id),
            product_id=data.product_id,
            user_id=user_id,
        )
        return serialize(doc)
    except DuplicateKeyError:
        logger.warning(
            "Duplicate review creation attempt for product_id={product_id}, user_id={user_id}",
            product_id=data.product_id,
            user_id=user_id,
        )
        raise HTTPException(status_code=409, detail="Review already exists; use PATCH to update")


async def get_reviews_for_product(product_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    REVIEWS_DB_REQUESTS_TOTAL.labels(service=SERVICE_NAME).inc()

    col = get_reviews_col()
    logger.info(
        "Fetching reviews for product_id={product_id} from DB (limit={limit}, offset={offset})",
        product_id=product_id,
        limit=limit,
        offset=offset,
    )
    cursor = (
        col.find({"product_id": product_id})
        .skip(offset).limit(limit)
        .sort("created_at", -1)
    )
    result = [serialize(d) async for d in cursor]
    logger.info(
        "Fetched {count} review(s) for product_id={product_id} from DB",
        count=len(result),
        product_id=product_id,
    )
    return result


async def get_all_reviews(limit: int = 50, offset: int = 0) -> list[dict]:
    REVIEWS_DB_REQUESTS_TOTAL.labels(service=SERVICE_NAME).inc()

    col = get_reviews_col()
    logger.info(
        "Fetching all reviews from DB (limit={limit}, offset={offset})",
        limit=limit,
        offset=offset,
    )
    cursor = col.find({}).skip(offset).limit(limit).sort("created_at", -1)
    result = [serialize(d) async for d in cursor]
    logger.info(
        "Fetched {count} review(s) from DB",
        count=len(result),
    )
    return result


async def get_review_by_id(review_id: str) -> dict:
    REVIEWS_DB_REQUESTS_TOTAL.labels(service=SERVICE_NAME).inc()

    col = get_reviews_col()
    logger.info(
        "Fetching review by id={review_id} from DB",
        review_id=review_id,
    )
    try:
        _id = ObjectId(review_id)
    except (InvalidId, TypeError):
        logger.warning(
            "Invalid review id='{review_id}' in get_review_by_id",
            review_id=review_id,
        )
        raise HTTPException(status_code=400, detail="Invalid review id")

    doc = await col.find_one({"_id": _id})
    if not doc:
        logger.warning(
            "Review not found in DB for id={review_id}",
            review_id=review_id,
        )
        raise HTTPException(status_code=404, detail="Review not found")
    logger.info(
        "Review fetched from DB for id={review_id}",
        review_id=review_id,
    )
    return serialize(doc)


async def update_review(user_id: str, review_id: str, data: ReviewUpdate, can_update_others: bool) -> dict:
    REVIEWS_DB_REQUESTS_TOTAL.labels(service=SERVICE_NAME).inc()

    col = get_reviews_col()
    logger.info(
        "Attempting to update review_id={review_id} for user_id={user_id} (can_update_others={can_update_others})",
        review_id=review_id,
        user_id=user_id,
        can_update_others=can_update_others,
    )
    query: dict[str, Any] = {"_id": _oid(review_id)}
    if not can_update_others:
        query["user_id"] = user_id

    update_fields: dict[str, Any] = {}
    if data.rating is not None:
        update_fields["rating"] = data.rating
    if data.text is not None:
        update_fields["text"] = data.text

    if not update_fields:
        logger.warning(
            "Update review called with no fields to update (review_id={review_id}, user_id={user_id})",
            review_id=review_id,
            user_id=user_id,
        )
        raise HTTPException(status_code=400, detail="Nothing to update")

    update_fields["updated_at"] = _now()

    doc = await col.find_one_and_update(
        query,
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        logger.warning(
            "Review not found in DB for update (review_id={review_id}, user_id={user_id}, can_update_others={can_update_others})",
            review_id=review_id,
            user_id=user_id,
            can_update_others=can_update_others,
        )
        raise HTTPException(status_code=404, detail="Review not found")
    logger.info(
        "Review updated in DB: review_id={review_id}",
        review_id=review_id,
    )
    return serialize(doc)


async def delete_review(user_id: str, review_id: str, can_delete_others: bool) -> dict:
    REVIEWS_DB_REQUESTS_TOTAL.labels(service=SERVICE_NAME).inc()

    col = get_reviews_col()
    logger.info(
        "Attempting to delete review_id={review_id} for user_id={user_id} (can_delete_others={can_delete_others})",
        review_id=review_id,
        user_id=user_id,
        can_delete_others=can_delete_others,
    )
    query: dict[str, Any] = {"_id": _oid(review_id)}
    if not can_delete_others:
        query["user_id"] = user_id

    doc = await col.find_one_and_delete(query)
    if not doc:
        logger.warning(
            "Review not found in DB for delete (review_id={review_id}, user_id={user_id}, can_delete_others={can_delete_others})",
            review_id=review_id,
            user_id=user_id,
            can_delete_others=can_delete_others,
        )
        raise HTTPException(status_code=404, detail="Review not found")
    logger.info(
        "Review deleted from DB: review_id={review_id}",
        review_id=review_id,
    )
    return {"status": "deleted", "id": str(doc["_id"])}
