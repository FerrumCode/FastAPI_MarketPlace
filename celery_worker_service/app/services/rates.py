from __future__ import annotations
import json
from decimal import Decimal
import asyncio
import httpx
import redis as redis_sync
from ..config import settings
from ..logging_conf import setup_logging

log = setup_logging()

KEY_USD_RUB = "rates:USD_RUB"
KEY_EUR_RUB = "rates:EUR_RUB"

def _redis():
    return redis_sync.Redis.from_url(settings.redis_url, decode_responses=True)

def fetch_stub_rates() -> dict[str, str]:
    """
    !!! ЗАГЛУШКА КУРСОВ !!!
    USD→RUB = 90, EUR→RUB = 95
    Если нет интеграции с провайдерами или EXCHANGE_PROVIDER=stub,
    будут возвращены эти значения.
    """
    return {"USD_RUB": "90.0", "EUR_RUB": "95.0"}

async def fetch_from_provider() -> dict[str, str] | None:
    provider = settings.exchange_provider.lower()
    api_key = settings.exchange_api_key
    base = settings.currency_base
    target = settings.currency_target

    # Если явно указали stub или нет ключей, отдаём заглушку
    if provider == "stub" or not api_key:
        return fetch_stub_rates()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if provider == "fixer" and settings.exchange_api_url:
                # прим.: https://data.fixer.io/api/latest?access_key=KEY&base=USD&symbols=RUB,EUR
                url = f"{settings.exchange_api_url}?access_key={api_key}&base={base}&symbols=RUB,EUR"
                r = await client.get(url)
                data = r.json()
                rub = data["rates"]["RUB"]
                eur = data["rates"]["EUR"] if base == "USD" else 1.0
                # нам важно USD->RUB и EUR->RUB
                if base == "USD":
                    usd_rub = rub
                    eur_rub = rub / eur
                else:
                    # если base не USD, можно добавить преобразование при желании
                    usd_rub = rub  # упрощение
                    eur_rub = rub
                return {"USD_RUB": str(usd_rub), "EUR_RUB": str(eur_rub)}
            # Аналогично можно добавить currencylayer/coinlayer/apilayer/currate/cbr
            # Здесь для краткости — если не fixer, вернём заглушку:
            return fetch_stub_rates()
    except Exception as e:
        log.error("fetch_rates_provider_error", error=str(e))
        return fetch_stub_rates()

def cache_rates(rates: dict[str, str]) -> None:
    r = _redis()
    ttl = settings.rates_ttl_seconds
    r.set(KEY_USD_RUB, rates["USD_RUB"], ex=ttl)
    r.set(KEY_EUR_RUB, rates["EUR_RUB"], ex=ttl)
    log.info("rates_cached", usd_rub=rates["USD_RUB"], eur_rub=rates["EUR_RUB"], ttl=ttl)

def get_rates() -> dict[str, Decimal]:
    r = _redis()
    usd = r.get(KEY_USD_RUB)
    eur = r.get(KEY_EUR_RUB)
    if usd and eur:
        return {"USD_RUB": Decimal(usd), "EUR_RUB": Decimal(eur)}
    # если в кэше нет — тянем и кешируем синхронно
    rates = asyncio.run(fetch_from_provider())
    cache_rates(rates)
    return {"USD_RUB": Decimal(rates["USD_RUB"]), "EUR_RUB": Decimal(rates["EUR_RUB"])}

def refresh_rates_sync():
    rates = asyncio.run(fetch_from_provider())
    cache_rates(rates)
    return rates
