from decimal import Decimal
from typing import Optional, Tuple
from uuid import uuid4

import redis
from loguru import logger

from env import RATES_REDIS_URL, RATES_CACHE_TTL_SECONDS, SERVICE_NAME, _LOCK_TTL_SECONDS_DEFAULT
from app.core.metrics import (
    RATES_CACHE_OPERATIONS_TOTAL,
    RATES_CACHE_PARSE_ERRORS_TOTAL,
    RATES_CACHE_GET_TOTAL,
)

_redis = redis.Redis.from_url(RATES_REDIS_URL, decode_responses=True)

_RELEASE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def _rate_key(base: str, target: str) -> str:
    return f"rates:{base.upper()}_{target.upper()}"


def _lock_key(base: str, target: str) -> str:
    return f"rates_lock:{base.upper()}_{target.upper()}"


def acquire_rate_lock(
    base: str,
    target: str,
    ttl_seconds: int = _LOCK_TTL_SECONDS_DEFAULT,
) -> Optional[Tuple[str, str]]:
    key = _lock_key(base, target)
    token = uuid4().hex
    try:
        ok = _redis.set(key, token, nx=True, ex=ttl_seconds)
    except redis.exceptions.RedisError as exc:
        logger.error("Redis SET NX failed for lock. key={key}, exc={exc}", key=key, exc=exc)
        return None

    return (key, token) if ok else None


def release_rate_lock(lock_key: str, token: str) -> None:
    try:
        _redis.eval(_RELEASE_LOCK_LUA, 1, lock_key, token)
    except redis.exceptions.RedisError as exc:
        logger.warning("Redis lock release failed. key={key}, exc={exc}", key=lock_key, exc=exc)


def peek_rate_from_cache(base: str, target: str) -> Optional[Decimal]:
    key = _rate_key(base, target)
    try:
        value = _redis.get(key)
    except redis.exceptions.RedisError:
        return None
    if value is None:
        return None
    try:
        return Decimal(value)
    except Exception:
        return None


def get_rate_from_cache(base: str, target: str) -> Optional[Decimal]:
    base_u = base.upper()
    target_u = target.upper()
    key = _rate_key(base_u, target_u)

    logger.info(
        "Getting rate from cache. key={key}, base={base}, target={target}",
        key=key,
        base=base_u,
        target=target_u,
    )

    try:
        value = _redis.get(key)
    except redis.exceptions.RedisError as exc:
        logger.error(
            "Redis GET failed. key={key}, base={base}, target={target}, exc={exc}",
            key=key,
            base=base_u,
            target=target_u,
            exc=exc,
        )
        RATES_CACHE_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="get",
            result="error",
        ).inc()
        RATES_CACHE_GET_TOTAL.labels(
            service=SERVICE_NAME,
            result="error",
            base=base_u,
            target=target_u,
        ).inc()
        return None

    if value is None:
        logger.info("Cache miss for exchange rate. key={key}", key=key)
        RATES_CACHE_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="get",
            result="miss",
        ).inc()
        RATES_CACHE_GET_TOTAL.labels(
            service=SERVICE_NAME,
            result="miss",
            base=base_u,
            target=target_u,
        ).inc()
        return None

    try:
        rate = Decimal(value)
        logger.info("Cache hit for exchange rate. key={key}, value={value}", key=key, value=value)
        RATES_CACHE_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="get",
            result="hit",
        ).inc()
        RATES_CACHE_GET_TOTAL.labels(
            service=SERVICE_NAME,
            result="hit",
            base=base_u,
            target=target_u,
        ).inc()
        return rate
    except Exception as exc:
        logger.warning(
            "Failed to parse cached rate for key={key}, value={value}: {exc}",
            key=key,
            value=value,
            exc=exc,
        )
        RATES_CACHE_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="get",
            result="error",
        ).inc()
        RATES_CACHE_GET_TOTAL.labels(
            service=SERVICE_NAME,
            result="error",
            base=base_u,
            target=target_u,
        ).inc()
        RATES_CACHE_PARSE_ERRORS_TOTAL.labels(service=SERVICE_NAME).inc()
        return None


def set_rate_to_cache(base: str, target: str, rate: Decimal) -> None:
    base_u = base.upper()
    target_u = target.upper()
    key = _rate_key(base_u, target_u)

    logger.info(
        "Setting rate to cache. key={key}, base={base}, target={target}, rate={rate}",
        key=key,
        base=base_u,
        target=target_u,
        rate=rate,
    )

    _redis.setex(key, RATES_CACHE_TTL_SECONDS, str(rate))
    RATES_CACHE_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="set",
        result="success",
    ).inc()
