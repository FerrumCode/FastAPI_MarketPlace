from decimal import Decimal
from typing import Optional

import redis
from loguru import logger

from env import RATES_REDIS_URL, RATES_CACHE_TTL_SECONDS, SERVICE_NAME
from app.core.metrics import RATES_CACHE_OPERATIONS_TOTAL, RATES_CACHE_PARSE_ERRORS_TOTAL


_redis = redis.Redis.from_url(RATES_REDIS_URL, decode_responses=True)


def get_rate_from_cache(base: str, target: str) -> Optional[Decimal]:
    key = f"rates:{base.upper()}_{target.upper()}"
    logger.info(
        "Getting rate from cache. key={key}, base={base}, target={target}",
        key=key,
        base=base,
        target=target,
    )
    value = _redis.get(key)
    if value is None:
        logger.info(
            "Cache miss for exchange rate. key={key}",
            key=key,
        )
        RATES_CACHE_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="get",
            result="miss",
        ).inc()
        return None
    try:
        rate = Decimal(value)
        logger.info(
            "Cache hit for exchange rate. key={key}, value={value}",
            key=key,
            value=value,
        )
        RATES_CACHE_OPERATIONS_TOTAL.labels(
            service=SERVICE_NAME,
            operation="get",
            result="hit",
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
        RATES_CACHE_PARSE_ERRORS_TOTAL.labels(
            service=SERVICE_NAME,
        ).inc()
        return None


def set_rate_to_cache(base: str, target: str, rate: Decimal) -> None:
    key = f"rates:{base.upper()}_{target.upper()}"
    logger.info(
        "Setting rate to cache. key={key}, base={base}, target={target}, rate={rate}",
        key=key,
        base=base,
        target=target,
        rate=rate,
    )
    _redis.setex(key, RATES_CACHE_TTL_SECONDS, str(rate))
    RATES_CACHE_OPERATIONS_TOTAL.labels(
        service=SERVICE_NAME,
        operation="set",
        result="success",
    ).inc()
