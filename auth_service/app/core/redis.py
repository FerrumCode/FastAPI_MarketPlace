from fastapi import FastAPI
import redis.asyncio as redis


redis_client: redis.Redis | None = None


async def init_redis(app: FastAPI) -> redis.Redis:
    global redis_client
    try:
        redis_client = redis.Redis(
            host="auth_redis",
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

        # Проверка соединения
        await redis_client.ping()
        print("✅ Redis подключён")

        app.state.redis = redis_client
        return redis_client

    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
        redis_client = None
        app.state.redis = None
        return None


async def get_redis() -> redis.Redis:
    if redis_client is None:
        raise RuntimeError("Redis клиент не инициализирован")
    return redis_client


async def set_refresh_token(user_id: int, token: str, expire_days: int):
    if redis_client is None:
        raise RuntimeError("Redis клиент не инициализирован")
    await redis_client.setex(f"refresh_{user_id}", expire_days * 24 * 3600, token)


async def get_refresh_token(user_id: int) -> str | None:
    if redis_client is None:
        raise RuntimeError("Redis клиент не инициализирован")
    return await redis_client.get(f"refresh_{user_id}")


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        await redis_client.connection_pool.disconnect()
        print("🔒 Redis закрыт")
        redis_client = None