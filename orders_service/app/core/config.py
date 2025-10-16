import os
from pydantic import BaseModel


class Settings(BaseModel):
    # БД уже берётся из твоего app/db.py — тут оставим для унификации.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@orders_db:5432/orders_db")

    # Внешние сервисы
    CATALOG_SERVICE_URL: str = os.getenv("CATALOG_SERVICE_URL", "http://catalog_service:8000")
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8000")

    # Kafka
    KAFKA_BROKER: str = os.getenv("KAFKA_BROKER", "kafka:9092")
    KAFKA_ORDER_TOPIC: str = os.getenv("KAFKA_ORDER_TOPIC", "order_events")

    # Валюта (для воркера пригодится в сообщении)
    CURRENCY_BASE: str = os.getenv("CURRENCY_BASE", "USD")
    TARGET_CURRENCY: str = os.getenv("TARGET_CURRENCY", "RUB")


settings = Settings()
