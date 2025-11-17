from decimal import Decimal
from typing import Optional

import redis

from env import RATES_REDIS_URL, RATES_CACHE_TTL_SECONDS

_redis = redis.Redis.from_url(RATES_REDIS_URL, decode_responses=True)


def get_rate_from_cache(base: str, target: str) -> Optional[Decimal]:
    key = f"rates:{base.upper()}_{target.upper()}"
    value = _redis.get(key)
    if value is None:
        return None
    try:
        return Decimal(value)
    except Exception:
        return None


def set_rate_to_cache(base: str, target: str, rate: Decimal) -> None:
    key = f"rates:{base.upper()}_{target.upper()}"
    _redis.setex(key, RATES_CACHE_TTL_SECONDS, str(rate))
