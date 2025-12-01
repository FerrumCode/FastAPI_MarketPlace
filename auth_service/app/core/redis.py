from fastapi import FastAPI
import redis.asyncio as redis
from loguru import logger

redis_client: redis.Redis | None = None


async def init_redis(app: FastAPI) -> redis.Redis:
    global redis_client
    logger.info("Инициализация подключения к Redis")
    try:
        redis_client = redis.Redis(
            host="auth_redis",
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

        await redis_client.ping()
        logger.info("Redis подключён и ping прошёл успешно")
        app.state.redis = redis_client
        return redis_client

    except Exception as e:
        logger.exception("Redis connection error")
        redis_client = None
        app.state.redis = None
        return None


async def get_redis() -> redis.Redis:
    if redis_client is None:
        logger.error("Попытка получить Redis-клиент до инициализации")
        logger.exception("Redis client don't inicialize")
        raise RuntimeError("Redis клиент не инициализирован")

    logger.info("Получен экземпляр Redis-клиента")
    return redis_client


async def set_refresh_token(user_id: int, token: str, expire_days: int):
    if redis_client is None:
        logger.error(
            "Попытка сохранить refresh-токен в Redis до инициализации клиента. user_id={user_id}",
            user_id=user_id,
        )
        logger.exception("Redis client don't inicialize")
        raise RuntimeError("Redis клиент не инициализирован")
    await redis_client.setex(f"refresh_{user_id}", expire_days * 24 * 3600, token)
    logger.info(
        "Refresh-токен сохранён в Redis для user_id={user_id}, срок действия {days} дней",
        user_id=user_id,
        days=expire_days,
    )


async def get_refresh_token(user_id: int) -> str | None:
    if redis_client is None:
        logger.error(
            "Попытка получить refresh-токен из Redis до инициализации клиента. user_id={user_id}",
            user_id=user_id,
        )
        logger.exception("Redis client don't inicialize")
        raise RuntimeError("Redis клиент не инициализирован")
    token = await redis_client.get(f"refresh_{user_id}")
    if token is None:
        logger.info("Refresh-токен для user_id={user_id} в Redis не найден", user_id=user_id)
    else:
        logger.info("Refresh-токен для user_id={user_id} успешно получен из Redis", user_id=user_id)
    return token


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        await redis_client.connection_pool.disconnect()
        logger.warning("Redis closed")
        redis_client = None
    else:
        logger.info("Попытка закрыть Redis, но клиент уже отсутствует или не инициализирован")
