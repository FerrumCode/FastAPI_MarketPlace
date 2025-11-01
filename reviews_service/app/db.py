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
        _db = _client.get_default_database()
        reviews_col = _db.get_collection("reviews")
        # Индексы
        await reviews_col.create_index([("product_id", ASCENDING), ("created_at", DESCENDING)])
        await reviews_col.create_index([("product_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
        logger.info("Mongo connected and indexes ensured")

def get_reviews_col():
    if reviews_col is None:
        raise RuntimeError("Mongo collection is not initialized yet (startup not finished)")
    return reviews_col

async def disconnect():
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("Mongo disconnected")
