import os
from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_ORDER_TOPIC = os.getenv("KAFKA_ORDER_TOPIC", "order_events")
KAFKA_REVIEW_TOPIC = os.getenv("KAFKA_REVIEW_TOPIC", "review_events")


REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8000")
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://catalog_service:8000")


CURRENCY_BASE = os.getenv("CURRENCY_BASE", "USD")
TARGET_CURRENCY = os.getenv("TARGET_CURRENCY", "RUB")