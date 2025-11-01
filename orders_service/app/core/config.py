import os
from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    # Postgres ордеров
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@orders_db:5432/orders_db",
    )

    # URL других микросервисов внутри docker compose
    CATALOG_SERVICE_URL: str = os.getenv(
        "CATALOG_SERVICE_URL",
        "http://catalog_service:8000",
    )

    AUTH_SERVICE_URL: str = os.getenv(
        "AUTH_SERVICE_URL",
        "http://auth_service:8000",
    )

    # Kafka
    KAFKA_BROKER: str = os.getenv("KAFKA_BROKER", "kafka:9092")
    KAFKA_ORDER_TOPIC: str = os.getenv("KAFKA_ORDER_TOPIC", "order_events")

    # Валюта
    CURRENCY_BASE: str = os.getenv("CURRENCY_BASE", "USD")
    TARGET_CURRENCY: str = os.getenv("TARGET_CURRENCY", "RUB")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_change_me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")


settings = Settings()


@lru_cache
def get_settings() -> Settings:
    # обёртка, чтобы один и тот же Settings использовать в db.py и т.д.
    return Settings()
