from decimal import Decimal

import requests
from loguru import logger
from prometheus_client import Counter

from .redis_cache import get_rate_from_cache, set_rate_to_cache
from env import (
    EXCHANGE_RATES_API_KEY,
    EXCHANGE_RATES_API_BASE_URL,
    EXCHANGE_RATES_API_TIMEOUT_SECONDS,
    SERVICE_NAME,
)

EXCHANGE_RATE_API_REQUESTS_TOTAL = Counter(
    "celery_worker_exchange_rate_api_requests_total",
    "External exchange rate API HTTP requests",
    ["service", "status", "base", "target"],
)

EXCHANGE_RATE_CACHE_TOTAL = Counter(
    "celery_worker_exchange_rate_cache_total",
    "Exchange rate cache hits and misses",
    ["service", "result", "base", "target"],
)

EXCHANGE_RATE_UPDATE_ALL_TOTAL = Counter(
    "celery_worker_exchange_rate_update_all_total",
    "Calls to update_all_rates()",
    ["service"],
)


def _fetch_rate_from_api(base: str, target: str) -> Decimal:
    base = base.upper()
    target = target.upper()

    logger.info(
        "Fetching exchange rate from API. base={base}, target={target}",
        base=base,
        target=target,
    )

    if base == target:
        logger.info(
            "Base and target currencies are equal in _fetch_rate_from_api. base={currency}",
            currency=base,
        )
        return Decimal("1.00")

    params = {
        "base": base,
        "symbols": target,
    }
    headers = {
        "apikey": EXCHANGE_RATES_API_KEY,
    }

    EXCHANGE_RATE_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        status="attempt",
        base=base,
        target=target,
    ).inc()


    try:
        response = requests.get(
            EXCHANGE_RATES_API_BASE_URL,
            params=params,
            headers=headers,
            timeout=EXCHANGE_RATES_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        EXCHANGE_RATE_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            status="timeout",
            base=base,
            target=target,
        ).inc()
        raise
    except requests.exceptions.HTTPError:
        EXCHANGE_RATE_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            status="http_error",
            base=base,
            target=target,
        ).inc()
        raise
    except requests.exceptions.RequestException:
        EXCHANGE_RATE_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            status="request_error",
            base=base,
            target=target,
        ).inc()
        raise

    try:
        data = response.json()
    except ValueError:
        EXCHANGE_RATE_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            status="json_error",
            base=base,
            target=target,
        ).inc()
        raise

    if not data.get("success", True):
        logger.error(
            "Exchange rates API returned error. base={base}, target={target}, data={data}",
            base=base,
            target=target,
            data=data,
        )
        EXCHANGE_RATE_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            status="api_error",
            base=base,
            target=target,
        ).inc()
        raise RuntimeError(f"API error: {data}")


    try:
        rate = data["rates"][target]
    except Exception:
        EXCHANGE_RATE_API_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            status="missing_rate",
            base=base,
            target=target,
        ).inc()
        raise

    logger.info(
        "Exchange rate fetched successfully. base={base}, target={target}, rate={rate}",
        base=base,
        target=target,
        rate=rate,
    )
    EXCHANGE_RATE_API_REQUESTS_TOTAL.labels(
        service=SERVICE_NAME,
        status="success",
        base=base,
        target=target,
    ).inc()
    return Decimal(str(rate))


def get_exchange_rate(base: str, target: str) -> Decimal:
    base = base.upper()
    target = target.upper()

    logger.info(
        "Getting exchange rate. base={base}, target={target}",
        base=base,
        target=target,
    )

    if base == target:
        logger.info(
            "Base and target currencies are equal in get_exchange_rate. base={currency}",
            currency=base,
        )
        return Decimal("1.00")

    cached = get_rate_from_cache(base, target)
    if cached is not None:
        logger.info(
            "Exchange rate found in cache. base={base}, target={target}, rate={rate}",
            base=base,
            target=target,
            rate=cached,
        )
        EXCHANGE_RATE_CACHE_TOTAL.labels(
            service=SERVICE_NAME,
            result="hit",
            base=base,
            target=target,
        ).inc()
        return cached

    EXCHANGE_RATE_CACHE_TOTAL.labels(
        service=SERVICE_NAME,
        result="miss",
        base=base,
        target=target,
    ).inc()
    logger.info(
        "Cache miss for exchange rate. base={base}, target={target}. Fetching from API",
        base=base,
        target=target,
    )

    rate = _fetch_rate_from_api(base, target)
    set_rate_to_cache(base, target, rate)
    logger.info(
        "Exchange rate cached. base={base}, target={target}, rate={rate}",
        base=base,
        target=target,
        rate=rate,
    )
    return rate


def update_all_rates() -> None:
    pairs = [
        ("USD", "RUB"),
        ("EUR", "RUB"),
    ]

    logger.info(
        "Updating all configured exchange rates. pairs={pairs}",
        pairs=pairs,
    )
    EXCHANGE_RATE_UPDATE_ALL_TOTAL.labels(
        service=SERVICE_NAME,
    ).inc()

    for base, target in pairs:
        logger.info(
            "Updating exchange rate pair. base={base}, target={target}",
            base=base,
            target=target,
        )
        rate = _fetch_rate_from_api(base, target)
        set_rate_to_cache(base, target, rate)
        logger.info(
            "Exchange rate updated. base={base}, target={target}, rate={rate}",
            base=base,
            target=target,
            rate=rate,
        )
