# services/exchange.py
from decimal import Decimal
import time

import requests
from loguru import logger

from .redis_cache import (
    get_rate_from_cache,
    set_rate_to_cache,
    acquire_rate_lock,
    release_rate_lock,
    peek_rate_from_cache,
)
from env import (
    EXCHANGE_RATES_API_KEY,
    EXCHANGE_RATES_API_BASE_URL,
    EXCHANGE_RATES_API_TIMEOUT_SECONDS,
    SERVICE_NAME,
)
from app.core.metrics import (
    EXCHANGE_RATE_API_REQUESTS_TOTAL,
    EXCHANGE_RATE_CACHE_TOTAL,
    EXCHANGE_RATE_UPDATE_ALL_TOTAL,
)

_WAIT_FOR_CACHE_FILL_SECONDS = 8.0
_WAIT_POLL_INTERVAL_SECONDS = 0.25
_API_MAX_ATTEMPTS = 2


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

    params = {"base": base, "symbols": target}
    headers = {"apikey": EXCHANGE_RATES_API_KEY}

    last_http_error: Exception | None = None

    for attempt_no in range(1, _API_MAX_ATTEMPTS + 1):
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
        except requests.exceptions.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code == 429:
                EXCHANGE_RATE_API_REQUESTS_TOTAL.labels(
                    service=SERVICE_NAME,
                    status="rate_limited",
                    base=base,
                    target=target,
                ).inc()

                retry_after = None
                try:
                    ra = exc.response.headers.get("Retry-After") if exc.response is not None else None
                    retry_after = int(ra) if ra is not None else None
                except Exception:
                    retry_after = None

                sleep_s = retry_after if (retry_after is not None and retry_after > 0) else 1
                sleep_s = min(sleep_s, 5)

                logger.warning(
                    "Exchange rate API rate limited (429). base={base}, target={target}, "
                    "attempt={attempt}/{max_attempts}, sleeping={sleep_s}s",
                    base=base,
                    target=target,
                    attempt=attempt_no,
                    max_attempts=_API_MAX_ATTEMPTS,
                    sleep_s=sleep_s,
                )

                last_http_error = exc
                if attempt_no < _API_MAX_ATTEMPTS:
                    time.sleep(sleep_s)
                    continue
            else:
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

    # If we ever got here (should be rare), raise the last HTTP error
    if last_http_error is not None:
        raise last_http_error
    raise RuntimeError("Failed to fetch exchange rate from API (unknown error)")


def get_exchange_rate(base: str, target: str) -> Decimal:
    base = base.upper()
    target = target.upper()

    logger.info("Getting exchange rate. base={base}, target={target}", base=base, target=target)

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
        "Cache miss for exchange rate. base={base}, target={target}. Trying single-flight lock",
        base=base,
        target=target,
    )

    lock = acquire_rate_lock(base, target)
    if lock is None:
        # Another worker is fetching. Wait a bit for the cache to be filled.
        deadline = time.monotonic() + _WAIT_FOR_CACHE_FILL_SECONDS
        while time.monotonic() < deadline:
            rate = peek_rate_from_cache(base, target)
            if rate is not None:
                logger.info(
                    "Exchange rate appeared in cache while waiting. base={base}, target={target}, rate={rate}",
                    base=base,
                    target=target,
                    rate=rate,
                )
                return rate
            time.sleep(_WAIT_POLL_INTERVAL_SECONDS)

        logger.warning(
            "Timed out waiting for cache fill. base={base}, target={target}. Falling back to API",
            base=base,
            target=target,
        )
        rate = _fetch_rate_from_api(base, target)
        set_rate_to_cache(base, target, rate)
        logger.info(
            "Exchange rate cached after fallback. base={base}, target={target}, rate={rate}",
            base=base,
            target=target,
            rate=rate,
        )
        return rate

    lock_key, token = lock
    try:
        # Double-check cache after acquiring lock (avoid duplicate API calls)
        rate = peek_rate_from_cache(base, target)
        if rate is not None:
            logger.info(
                "Exchange rate already in cache after lock acquired. base={base}, target={target}, rate={rate}",
                base=base,
                target=target,
                rate=rate,
            )
            return rate

        rate = _fetch_rate_from_api(base, target)
        set_rate_to_cache(base, target, rate)
        logger.info(
            "Exchange rate cached. base={base}, target={target}, rate={rate}",
            base=base,
            target=target,
            rate=rate,
        )
        return rate
    finally:
        release_rate_lock(lock_key, token)


def update_all_rates() -> None:
    pairs = [
        ("USD", "RUB"),
        ("EUR", "RUB"),
    ]

    logger.info("Updating all configured exchange rates. pairs={pairs}", pairs=pairs)

    EXCHANGE_RATE_UPDATE_ALL_TOTAL.labels(service=SERVICE_NAME).inc()

    for base, target in pairs:
        logger.info("Updating exchange rate pair. base={base}, target={target}", base=base, target=target)
        rate = _fetch_rate_from_api(base, target)
        set_rate_to_cache(base, target, rate)
        logger.info("Exchange rate updated. base={base}, target={target}, rate={rate}", base=base, target=target, rate=rate)
