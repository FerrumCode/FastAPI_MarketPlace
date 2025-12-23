from prometheus_client import Counter, Gauge, Histogram

REDIS_OPS = Counter(
    "auth_redis_ops",
    "Redis operations",
    ["service", "operation", "status"],
)

REDIS_CONNECTION_STATUS = Gauge(
    "auth_redis_connection_status",
    "Redis connection status (1=connected, 0=disconnected)",
    ["service"],
)

JWT_ACCESS_VALIDATION_TOTAL = Counter(
    "auth_auth_jwt_access_validation_total",
    "Access JWT validation events",
    ["service", "result"],
)

REFRESH_BLACKLIST_CHECKS_TOTAL = Counter(
    "auth_refresh_blacklist_checks_total",
    "Refresh token blacklist checks",
    ["service", "result"],
)

PERMISSION_CHECKS_TOTAL = Counter(
    "auth_auth_permission_checks_total",
    "Permission checks based on JWT",
    ["service", "permission", "result"],
)

HTTP_REQUESTS_TOTAL = Counter(
    "auth_http_requests_total",
    "Total HTTP requests",
    ["service", "method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "auth_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["service", "method", "path"],
)

ACCESS_TOKENS_ISSUED_TOTAL = Counter(
    "auth_access_tokens_issued_total",
    "Access tokens created",
    ["service", "role_name"],
)

REFRESH_TOKENS_ISSUED_TOTAL = Counter(
    "auth_refresh_tokens_issued_total",
    "Refresh tokens created",
    ["service", "role_name"],
)

AUTHENTICATION_ATTEMPTS_TOTAL = Counter(
    "auth_authentication_attempts_total",
    "User authentication attempts",
    ["service", "result"],
)
