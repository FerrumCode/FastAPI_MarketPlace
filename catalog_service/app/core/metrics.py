from prometheus_client import Counter, Gauge, Histogram


KAFKA_OPS = Counter(
    "catalog_kafka_ops",
    "Kafka producer operations",
    ["service", "operation", "status"],
)

KAFKA_CONNECTION_STATUS = Gauge(
    "catalog_kafka_connection_status",
    "Kafka producer connection status (1=connected, 0=disconnected)",
    ["service"],
)

REDIS_OPS = Counter(
    "catalog_redis_ops",
    "Redis operations",
    ["service", "operation", "status"],
)

REDIS_CONNECTION_STATUS = Gauge(
    "catalog_redis_connection_status",
    "Redis connection status (1=connected, 0=disconnected)",
    ["service"],
)

JWT_ACCESS_VALIDATION_TOTAL = Counter(
    "catalog_auth_jwt_access_validation_total",
    "Access JWT validation events",
    ["service", "result"],
)

PERMISSION_CHECKS_TOTAL = Counter(
    "catalog_auth_permission_checks_total",
    "Permission checks based on JWT",
    ["service", "permission", "result"],
)
HTTP_REQUESTS_TOTAL = Counter(
    "catalog_http_requests_total",
    "Total HTTP requests",
    ["service", "method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "catalog_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "method", "path"],
)

CATEGORIES_OPERATIONS_TOTAL = Counter(
    "catalog_categories_operations_total",
    "Category endpoint operations",
    ["service", "operation", "status"],
)

PRODUCTS_OPERATIONS_TOTAL = Counter(
    "catalog_products_operations_total",
    "Product endpoint operations",
    ["service", "operation", "status"],
)