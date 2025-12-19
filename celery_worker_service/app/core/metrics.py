from prometheus_client import Counter, Gauge, Histogram


EXCHANGE_RATE_API_REQUESTS_TOTAL = Counter(
    "celery_worker_exchange_rate_api_requests_total",
    "External exchange rate API HTTP requests",
    ["service", "status", "base", "target"],
)

EXCHANGE_RATE_CACHE_TOTAL = Counter(
    "celery_worker_exchange_rate_cache_total",
    "Exchange rate cache hits and misses",
    ["service", "result", "base", "target"],
)

EXCHANGE_RATE_UPDATE_ALL_TOTAL = Counter(
    "celery_worker_exchange_rate_update_all_total",
    "Calls to update_all_rates()",
    ["service"],
)

KAFKA_CONSUMER_START_TOTAL = Counter(
    "celery_worker_kafka_consumer_start_total",
    "Kafka consumer start attempts",
    ["service", "status"],
)

KAFKA_CONSUMER_MESSAGES_TOTAL = Counter(
    "celery_worker_kafka_consumer_messages_total",
    "Kafka messages processed by consumer",
    ["service", "topic", "event_type", "result"],
)

KAFKA_CONSUMER_ERRORS_TOTAL = Counter(
    "celery_worker_kafka_consumer_errors_total",
    "Kafka consumer errors in main loop",
    ["service", "error_type"],
)

ORDERS_REPO_REQUESTS_TOTAL = Counter(
    "celery_worker_orders_repo_requests_total",
    "HTTP requests from celery worker to Orders service",
    ["service", "method", "endpoint", "status"],
)

ORDERS_REPO_ERRORS_TOTAL = Counter(
    "celery_worker_orders_repo_errors_total",
    "Errors while calling Orders service from celery worker",
    ["service", "method", "endpoint", "error_type"],
)

RATES_CACHE_OPERATIONS_TOTAL = Counter(
    "celery_worker_rates_cache_operations_total",
    "Redis operations for exchange rates cache",
    ["service", "operation", "result"],
)

RATES_CACHE_GET_TOTAL = Counter(
    "celery_worker_rates_cache_get_total",
    "Redis GET hits and misses for exchange rates cache (by currency pair)",
    ["service", "result", "base", "target"],
)

RATES_CACHE_PARSE_ERRORS_TOTAL = Counter(
    "celery_worker_rates_cache_parse_errors_total",
    "Failed to parse cached exchange rate value",
    ["service"],
)

DELIVERY_CALCULATIONS_TOTAL = Counter(
    "celery_worker_delivery_calculations_total",
    "Delivery price calculation events",
    ["service", "result"],
)

DELIVERY_PRICE_RUB = Histogram(
    "celery_worker_delivery_price_rub",
    "Calculated delivery prices in RUB",
    ["service"],
)

TASKS_STARTED = Counter(
    "celery_worker_tasks_started_total",
    "Number of Celery tasks started",
    ["task_name"],
)

TASKS_SUCCEEDED = Counter(
    "celery_worker_tasks_succeeded_total",
    "Number of Celery tasks succeeded",
    ["task_name"],
)

TASKS_FAILED = Counter(
    "celery_worker_tasks_failed_total",
    "Number of Celery tasks failed",
    ["task_name"],
)

TASKS_RETRIED = Counter(
    "celery_worker_tasks_retried_total",
    "Number of Celery task executions that ended with RETRY state",
    ["task_name"],
)

TASKS_FAILED_BY_EXCEPTION = Counter(
    "celery_worker_tasks_failed_by_exception_total",
    "Number of Celery task failures by exception type",
    ["task_name", "exc_type"],
)

TASKS_IN_PROGRESS = Gauge(
    "celery_worker_tasks_in_progress",
    "Number of Celery tasks currently running",
    ["task_name"],
)

TASK_RUNTIME = Histogram(
    "celery_worker_task_runtime_seconds",
    "Celery task runtime in seconds",
    ["task_name"],
)
