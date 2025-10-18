from datetime import datetime
from typing import Any, Mapping

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.db import get_reviews_col   # <-- вместо "from app.db import reviews_col"
from app.schemas.review import ReviewCreate, ReviewUpdate


def _now() -> datetime:
    return datetime.utcnow()


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
    col = get_reviews_col()
    doc = {
        "product_id": data.product_id,
        "user_id": user_id,
        "rating": data.rating,
        "text": data.text or "",
        "created_at": _now(),
        "updated_at": _now(),
    }
    try:
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return serialize(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Review already exists; use PATCH to update")


async def get_reviews_for_product(product_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    col = get_reviews_col()
    cursor = col.find({"product_id": product_id}).skip(offset).limit(limit).sort("created_at", -1)
    return [serialize(d) async for d in cursor]


async def update_review(user_id: str, product_id: str, data: ReviewUpdate, can_update_others: bool) -> dict:
    col = get_reviews_col()
    query: dict[str, Any] = {"product_id": product_id}
    if not can_update_others:
        query["user_id"] = user_id

    update_fields: dict[str, Any] = {}
    if data.rating is not None:
        update_fields["rating"] = data.rating
    if data.text is not None:
        update_fields["text"] = data.text

    if not update_fields:
        raise HTTPException(status_code=400, detail="Nothing to update")

    update_fields["updated_at"] = _now()

    doc = await col.find_one_and_update(
        query,
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Review not found")
    return serialize(doc)


async def delete_review(user_id: str, product_id: str, can_delete_others: bool) -> dict:
    col = get_reviews_col()
    query: dict[str, Any] = {"product_id": product_id}
    if not can_delete_others:
        query["user_id"] = user_id

    doc = await col.find_one_and_delete(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"status": "deleted", "id": str(doc["_id"])}
