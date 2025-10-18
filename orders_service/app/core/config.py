import os
from pydantic import BaseModel


class Settings(BaseModel):
    # DB (тут просто для унификации; фактически БД инициализируешь в app/db.py)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@orders_db:5432/orders_db")

    # Сервисы
    CATALOG_SERVICE_URL: str = os.getenv("CATALOG_SERVICE_URL", "http://127.0.0.1:8001")
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8000")

    # Kafka
    KAFKA_BROKER: str = os.getenv("KAFKA_BROKER", "kafka:9092")
    KAFKA_ORDER_TOPIC: str = os.getenv("KAFKA_ORDER_TOPIC", "order_events")

    # Валюта
    CURRENCY_BASE: str = os.getenv("CURRENCY_BASE", "USD")
    TARGET_CURRENCY: str = os.getenv("TARGET_CURRENCY", "RUB")

    # JWT — берём ровно те имена, что в твоём .env
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_change_me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")


settings = Settings()
