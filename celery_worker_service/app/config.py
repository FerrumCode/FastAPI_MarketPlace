from pydantic import BaseModel
import os

class Settings(BaseModel):
    service_name: str = os.getenv("SERVICE_NAME", "celery_worker_service")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    redis_host: str = os.getenv("REDIS_HOST", "celery_redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    kafka_broker: str = os.getenv("KAFKA_BROKER", "kafka:9092")
    kafka_topic_orders: str = os.getenv("KAFKA_ORDER_EVENTS_TOPIC", "order_events")
    kafka_group: str = os.getenv("KAFKA_ORDER_EVENTS_GROUP", "celery-worker-group")

    pg_host: str = os.getenv("POSTGRES_HOST", "orders_db")
    pg_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_db: str = os.getenv("POSTGRES_DB", "orders_db")
    pg_user: str = os.getenv("POSTGRES_USER", "postgres")
    pg_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")

    currency_base: str = os.getenv("CURRENCY_BASE", "USD")
    currency_target: str = os.getenv("CURRENCY_TARGET", "RUB")
    rates_ttl_seconds: int = int(os.getenv("RATES_TTL_SECONDS", "86400"))
    exchange_provider: str = os.getenv("EXCHANGE_PROVIDER", "stub")
    exchange_api_key: str | None = os.getenv("EXCHANGE_API_KEY") or None
    exchange_api_url: str | None = os.getenv("EXCHANGE_API_URL") or None

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def sqlalchemy_url(self) -> str:
        return f"postgresql+psycopg2://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}"

settings = Settings()
