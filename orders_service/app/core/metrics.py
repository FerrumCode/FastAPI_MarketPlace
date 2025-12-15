from prometheus_client import Counter, Gauge, Histogram


CATALOG_FETCH_PRODUCT_TOTAL = Counter(
    "orders_catalog_fetch_product_total",
    "Fetch product requests to Catalog Service",
    ["service", "status"],
)

KAFKA_PRODUCER_START_TOTAL = Counter(
    "orders_kafka_producer_start_total",
    "Kafka producer start events",
    ["service", "result"],
)

KAFKA_PRODUCER_STOP_TOTAL = Counter(
    "orders_kafka_producer_stop_total",
    "Kafka producer stop events",
    ["service", "result"],
)

KAFKA_PRODUCER_MESSAGES_TOTAL = Counter(
    "orders_kafka_producer_messages_total",
    "Kafka producer send events",
    ["service", "result"],
)

ORDER_ITEMS_DB_OPERATIONS_TOTAL = Counter(
    "orders_order_items_db_operations_total",
    "Order items DB operations",
    ["service", "operation", "status"],
)

ORDERS_DB_OPERATIONS_TOTAL = Counter(
    "orders_orders_db_operations_total",
    "Orders DB operations",
    ["service", "operation", "status"],
)

AUTH_TOKEN_VALIDATION_TOTAL = Counter(
    "orders_auth_token_validation_total",
    "Authentication token validation events in Orders service",
    ["service", "result"],
)

PERMISSION_CHECK_TOTAL = Counter(
    "orders_permission_check_total",
    "Permission check events in Orders service",
    ["service", "permission", "result"],
)

HTTP_REQUESTS_TOTAL = Counter(
    "orders_http_requests_total",
    "Total HTTP requests",
    ["service", "method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "orders_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["service", "method", "path"],
)

ORDERS_API_REQUESTS_TOTAL = Counter(
    "orders_orders_api_requests_total",
    "Orders API request events",
    ["service", "endpoint", "method", "status"],
)

ORDER_ITEMS_API_REQUESTS_TOTAL = Counter(
    "orders_order_items_api_requests_total",
    "Order items CRUD API request events",
    ["service", "endpoint", "method", "status"],
)

ORDERS_SERVICE_OPERATIONS_TOTAL = Counter(
    "orders_service_operations_total",
    "Order service operations",
    ["service", "operation", "status"],
)
