import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"

    AUTH_SERVICE_URL: str | None = None
    CATALOG_SERVICE_URL: str | None = None

    KAFKA_BROKER: str = "kafka:9092"
    KAFKA_REVIEW_TOPIC: str = "review_events"

    MONGO_URL: str = "mongodb://reviews_mongo:27017/reviews_db"
    MONGO_DB: str = "reviews_db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
