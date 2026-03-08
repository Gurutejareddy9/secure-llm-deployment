"""Prometheus metrics definitions for the LLM gateway."""

from prometheus_client import Counter, Gauge, Histogram

# Total LLM API requests, labelled by endpoint and status
REQUEST_COUNTER = Counter(
    "llm_requests_total",
    "Total number of LLM API requests",
    labelnames=["endpoint", "status"],
)

# Request duration histogram
REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    labelnames=["model"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

# Total tokens consumed
TOKENS_USED = Counter(
    "llm_tokens_used_total",
    "Total number of LLM tokens consumed",
    labelnames=["model"],
)

# Total API cost in USD
COST_TOTAL = Counter(
    "llm_cost_total",
    "Cumulative LLM API cost in USD",
    labelnames=["model"],
)

# Cache hits
CACHE_HITS = Counter(
    "llm_cache_hits_total",
    "Total number of semantic cache hits",
)

# Security blocks
SECURITY_BLOCKS = Counter(
    "llm_security_blocks_total",
    "Total number of requests blocked by the security layer",
    labelnames=["reason"],
)

# Currently active requests
ACTIVE_REQUESTS = Gauge(
    "llm_active_requests",
    "Number of LLM requests currently being processed",
)
