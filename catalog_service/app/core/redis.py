import os
from fastapi import FastAPI
import redis.asyncio as redis
from loguru import logger
from app.core.metrics import REDIS_OPS, REDIS_CONNECTION_STATUS

SERVICE_NAME = "catalog_service"


redis_client: redis.Redis | None = None


async def init_redis(app: FastAPI):
    global redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    logger.info(
        "Initializing Redis client for service={service}, url={url}",
        service=SERVICE_NAME,
        url=redis_url,
    )

    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        app.state.redis = redis_client

        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(1)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="init",
            status="success",
        ).inc()

        logger.info("Redis client initialized successfully for service={service}", service=SERVICE_NAME)

    except Exception:
        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="init",
            status="error",
        ).inc()

        logger.exception(
            "Redis client initialization failed for service={service}",
            service=SERVICE_NAME,
        )
        raise


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis client closed for service={service}", service=SERVICE_NAME)

        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="close",
            status="success",
        ).inc()
    else:
        logger.info(
            "Attempt to close Redis client, but it is not initialized for service={service}",
            service=SERVICE_NAME,
        )
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="close",
            status="noop",
        ).inc()


async def get_redis() -> redis.Redis:
    if redis_client is None:
        logger.error(
            "Attempt to get Redis client before initialization for service={service}",
            service=SERVICE_NAME,
        )

        REDIS_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        REDIS_OPS.labels(
            service=SERVICE_NAME,
            operation="get_client",
            status="error",
        ).inc()

        raise RuntimeError("Redis клиент не инициализирован")

    logger.info("Redis client instance obtained for service={service}", service=SERVICE_NAME)

    REDIS_OPS.labels(
        service=SERVICE_NAME,
        operation="get_client",
        status="success",
    ).inc()

    return redis_client
