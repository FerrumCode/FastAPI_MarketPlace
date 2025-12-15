import os

SERVICE_NAME = os.getenv("SERVICE_NAME")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://celery_worker_redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://celery_worker_redis:6379/1")

RATES_REDIS_URL = os.getenv("RATES_REDIS_URL", "redis://celery_worker_redis:6379/2")
RATES_CACHE_TTL_SECONDS = int(os.getenv("RATES_CACHE_TTL_SECONDS", "3600"))

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_ORDER_TOPIC = os.getenv("KAFKA_ORDER_TOPIC", "order_events")
KAFKA_CONSUMER_GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP_ID", "celery_worker_service")

ORDERS_SERVICE_URL = os.getenv("ORDERS_SERVICE_URL", "http://orders_service:8000")
ORDERS_SERVICE_TOKEN = os.getenv("ORDERS_SERVICE_TOKEN", "")

DEFAULT_TARGET_CURRENCY = os.getenv("DEFAULT_TARGET_CURRENCY", "RUB")

EXCHANGE_RATES_API_KEY = os.getenv("EXCHANGE_RATES_API_KEY", "")
EXCHANGE_RATES_API_BASE_URL = os.getenv(
    "EXCHANGE_RATES_API_BASE_URL",
    "https://api.apilayer.com/exchangerates_data/latest",
)
EXCHANGE_RATES_API_TIMEOUT_SECONDS = int(os.getenv("EXCHANGE_RATES_API_TIMEOUT_SECONDS", "5"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9000"))
PROMETHEUS_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "/tmp/celery_prometheus_multiproc")
METRICS_BEARER_TOKEN_FILE = os.getenv("METRICS_BEARER_TOKEN_FILE", "/run/secrets/celery_worker_metrics.jwt")

os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", PROMETHEUS_MULTIPROC_DIR)
