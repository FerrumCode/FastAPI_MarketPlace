import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from app.core.config import settings


logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db = None
reviews_col = None


async def connect():
    global _client, _db, reviews_col
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL)
        _db = _client.get_default_database() if _client else None
        reviews_col = _db.get_collection("reviews")
        # Индексы: быстрый поиск по product_id и уникальность (product_id, user_id)
        await reviews_col.create_index([("product_id", ASCENDING), ("created_at", DESCENDING)])
        await reviews_col.create_index([("product_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
        logger.info("Mongo connected and indexes ensured")


async def disconnect():
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("Mongo disconnected")
