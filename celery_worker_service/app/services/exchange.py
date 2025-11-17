from decimal import Decimal

import requests

from .redis_cache import get_rate_from_cache, set_rate_to_cache

API_KEY = "llUHQGa7iAgIGk9sIi0gX4CETHXM6QjA"
BASE_URL = "https://api.apilayer.com/exchangerates_data/latest"
TIMEOUT = 5


def _fetch_rate_from_api(base: str, target: str) -> Decimal:
    base = base.upper()
    target = target.upper()

    if base == target:
        return Decimal("1.00")

    params = {
        "base": base,
        "symbols": target,
    }
    headers = {
        "apikey": API_KEY,
    }

    response = requests.get(BASE_URL, params=params, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()

    data = response.json()

    if not data.get("success", True):
        raise RuntimeError(f"API error: {data}")

    rate = data["rates"][target]
    return Decimal(str(rate))


def get_exchange_rate(base: str, target: str) -> Decimal:
    base = base.upper()
    target = target.upper()

    if base == target:
        return Decimal("1.00")

    cached = get_rate_from_cache(base, target)
    if cached is not None:
        return cached

    rate = _fetch_rate_from_api(base, target)
    set_rate_to_cache(base, target, rate)
    return rate


def update_all_rates() -> None:
    pairs = [
        ("USD", "RUB"),
        ("EUR", "RUB"),
    ]

    for base, target in pairs:
        rate = _fetch_rate_from_api(base, target)
        set_rate_to_cache(base, target, rate)
