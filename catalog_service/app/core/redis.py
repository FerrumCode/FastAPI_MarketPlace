# import redis.asyncio as redis
# from fastapi import FastAPI
#
#
# redis_client: redis.Redis | None = None
#
#
# async def init_redis(app: FastAPI):
#     global redis_client
#     redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
#     app.state.redis = redis_client
#
#
# async def close_redis():
#     if redis_client:
#         await redis_client.close()
#
#
# def get_redis() -> redis.Redis:
#     return redis_client


import os
import redis.asyncio as redis
from fastapi import FastAPI

redis_client: redis.Redis | None = None

async def init_redis(app: FastAPI):
    global redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    app.state.redis = redis_client

async def close_redis():
    if redis_client:
        await redis_client.close()

async def get_redis() -> redis.Redis:
    if redis_client is None:
        raise RuntimeError("Redis клиент не инициализирован")
    return redis_client
