from fastapi import FastAPI
import redis.asyncio as redis
from loguru import logger
from prometheus_client import Counter, Gauge

SERVICE_NAME = "auth_service"


REDIS_OPS = Counter(
    "auth_redis_ops",
    "Redis operations",
    ["service", "operation", "status"],
)


REDIS_CONNECTION_STATUS = Gauge(
    "auth_redis_connection_status",
    "Redis connection status (1=connected, 0=disconnected)",
    ["service"],
)

redis_client: redis.Redis | None = None


async def init_redis(app: FastAPI) -> redis.Redis:
    global redis_client
    logger.info("Initializing connection to Redis")
    try:
        redis_client = redis.Redis(
            host="auth_redis",
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

        await redis_client.ping()
        logger.info("Redis connected and ping successful")
        app.state.redis = redis_client

        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(1)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="ping",
            status="success",
        ).inc()

        return redis_client

    except Exception as e:
        logger.exception("Redis connection error")
        redis_client = None
        app.state.redis = None

        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="ping",
            status="error",
        ).inc()

        return None


async def get_redis() -> redis.Redis:
    if redis_client is None:
        logger.error("Attempt to get Redis client before initialization")
        logger.debug("Redis client is not initialized")

        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="get_client",
            status="error",
        ).inc()

        raise RuntimeError("Redis client is not initialized")

    logger.info("Redis client instance obtained")

    REDIS_OPS.labels(
        service=SERVICE_NAME,
        operation="get_client",
        status="success",
    ).inc()

    return redis_client


async def set_refresh_token(user_id: int, token: str, expire_days: int):
    if redis_client is None:
        logger.error(
            "Attempt to save refresh token to Redis before client initialization. user_id={user_id}",
            user_id=user_id,
        )
        logger.debug("Redis client is not initialized")

        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="set_refresh_token",
            status="error",
        ).inc()

        raise RuntimeError("Redis client is not initialized")

    await redis_client.setex(f"refresh_{user_id}", expire_days * 24 * 3600, token)

    REDIS_OPS.labels(
        service=SERVICE_NAME,
        operation="set_refresh_token",
        status="success",
    ).inc()

    logger.info(
        "Refresh token saved in Redis for user_id={user_id}, expires in {days} days",
        user_id=user_id,
        days=expire_days,
    )


async def get_refresh_token(user_id: int) -> str | None:
    if redis_client is None:
        logger.error(
            "Attempt to get refresh token from Redis before client initialization. user_id={user_id}",
            user_id=user_id,
        )
        logger.debug("Redis client is not initialized")

        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="get_refresh_token",
            status="error",
        ).inc()

        raise RuntimeError("Redis client is not initialized")

    token = await redis_client.get(f"refresh_{user_id}")
    if token is None:
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="get_refresh_token",
            status="miss",
        ).inc()
        logger.info("Refresh token for user_id={user_id} not found in Redis", user_id=user_id)
    else:
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="get_refresh_token",
            status="hit",
        ).inc()
        logger.info(
            "Refresh token for user_id={user_id} successfully retrieved from Redis",
            user_id=user_id,
        )
    return token


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        await redis_client.connection_pool.disconnect()
        logger.info("Redis closed")

        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="close",
            status="success",
        ).inc()

        redis_client = None
    else:
        logger.info("Attempt to close Redis, but the client is already missing or not initialized")
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="close",
            status="noop",
        ).inc()
