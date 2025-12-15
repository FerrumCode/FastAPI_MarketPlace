from prometheus_client import Counter, Gauge, Histogram


KAFKA_PRODUCER_START_TOTAL = Counter(
    "reviews_kafka_producer_start_total",
    "Kafka producer start events",
    ["service", "result"],
)

KAFKA_PRODUCER_STOP_TOTAL = Counter(
    "reviews_kafka_producer_stop_total",
    "Kafka producer stop events",
    ["service", "result"],
)

KAFKA_SEND_TOTAL = Counter(
    "reviews_kafka_send_total",
    "Kafka send events",
    ["service", "result"],
)

AUTH_TOKEN_VALIDATION_TOTAL = Counter(
    "reviews_auth_token_validation_total",
    "Token validation events",
    ["service", "result"],
)

AUTH_PERMISSION_CHECK_TOTAL = Counter(
    "reviews_auth_permission_check_total",
    "Permission check events",
    ["service", "result", "permission"],
)

HTTP_REQUESTS_TOTAL = Counter(
    "reviews_http_requests_total",
    "Total HTTP requests",
    ["service", "method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "reviews_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "method", "path"],
)

REVIEWS_CREATE_TOTAL = Counter(
    "reviews_create_total",
    "Review creation events",
    ["service", "status"],
)

REVIEWS_GET_TOTAL = Counter(
    "reviews_get_total",
    "Get reviews for product events",
    ["service", "status"],
)

REVIEWS_GET_BY_ID_TOTAL = Counter(
    "reviews_get_by_id_total",
    "Get review by id events",
    ["service", "status"],
)

REVIEWS_PATCH_TOTAL = Counter(
    "reviews_patch_total",
    "Review patch events",
    ["service", "status"],
)

REVIEWS_DELETE_TOTAL = Counter(
    "reviews_delete_total",
    "Review delete events",
    ["service", "status"],
)

REVIEWS_DB_REQUESTS_TOTAL = Counter(
    "reviews_db_requests_total",
    "Total DB requests for reviews (used to calculate RPS/RPM)",
    ["service"],
)