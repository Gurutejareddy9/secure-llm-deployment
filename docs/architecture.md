# System Architecture

## Overview

The Secure LLM Deployment Gateway is a layered API service that sits between clients and LLM backends. Every request traverses a security pipeline before reaching the model, and every response is filtered before being returned.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                          Internet / Client                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │ HTTPS
┌───────────────────────────────▼──────────────────────────────────┐
│                      API Gateway (FastAPI)                        │
│  ┌──────────────┐  ┌────────────────┐  ┌───────────────────────┐ │
│  │  JWT Auth    │  │  Rate Limiter  │  │  CORS + Middleware    │ │
│  └──────────────┘  └────────────────┘  └───────────────────────┘ │
└───────────────────────────────┬──────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────┐
│                        Security Layer                             │
│  ┌──────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ Input Sanitizer  │→ │  Prompt Guard   │→ │   PII Filter   │  │
│  └──────────────────┘  └─────────────────┘  └────────────────┘  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
               ┌────────────────▼─────────────────┐
               │        Redis Cache Layer          │
               │  Exact-key + Semantic Similarity  │
               └──────────┬──────────┬─────────────┘
                     MISS │          │ HIT → return
               ┌──────────▼──────┐   │
               │  Query Router   │   │
               │ small / large   │   │
               └──────┬──────────┘   │
                      │              │
          ┌───────────▼──────────┐   │
          │   Inference Engine   │   │
          │  Batch Processor     │   │
          │  (OpenAI / HuggingFace / Mock)  │
          └───────────┬──────────┘   │
                      │              │
          ┌───────────▼──────────┐   │
          │   Output Filter      │   │
          │ Safety + PII Redact  │   │
          └───────────┬──────────┘   │
                      └──────────────┘
                             │
┌──────────────────────────── ▼─────────────────────────────────────┐
│                      Monitoring Stack                              │
│   Prometheus Metrics  │  Structured Logging  │  Grafana Dashboards│
└────────────────────────────────────────────────────────────────────┘
```

## Components

### API Gateway (`src/api_gateway/`)
- **app.py** – FastAPI application factory with CORS, rate-limiting, and middleware.
- **routes.py** – Endpoint definitions: `/health`, `/api/v1/token`, `/api/v1/query`, `/metrics`.
- **auth.py** – JWT token creation and validation using `python-jose`.
- **middleware.py** – Assigns unique `X-Request-ID` to every request and logs timing.

### Security Layer (`src/security/`)
- **input_sanitizer.py** – Strips HTML, control chars; enforces length limits.
- **prompt_guard.py** – 20+ regex patterns for injection detection with confidence scoring.
- **pii_filter.py** – Regex-based PII detection with mask/remove/replace redaction modes.
- **output_filter.py** – Harmful-content check and PII redaction on LLM outputs.

### Cache Layer (`src/cache/`)
- **response_cache.py** – Redis-backed cache with SHA-256 exact key lookup and cosine-similarity semantic lookup using `sentence-transformers`.

### Routing Layer (`src/routing/`)
- **query_router.py** – Heuristic complexity scoring (length + keywords + sentence count) to select the cheapest capable model.

### Inference Layer (`src/inference/`)
- **engine.py** – Abstract backend with OpenAI and Mock implementations; retries, timeout, cost tracking.
- **batch_processor.py** – Priority queue with configurable batch size and flush interval.
- **model_loader.py** – HuggingFace model loader with 4-bit / 8-bit quantization support.

### Monitoring (`src/monitoring/`)
- **metrics.py** – Prometheus counters, histograms, and gauges.
- **logger.py** – Structlog-based JSON logging with request-ID context.

## Data Flow

1. Client sends POST `/api/v1/query` with a Bearer token.
2. JWT middleware validates the token; rejected if invalid.
3. Rate limiter checks the request count for the client IP.
4. Input sanitizer cleans the text.
5. Prompt guard scans for injection; blocks if confidence ≥ threshold.
6. PII filter redacts sensitive data from the input.
7. Cache is checked (exact then semantic); returns cached response if found.
8. Query router assigns a model tier.
9. Inference engine calls the LLM with retry logic.
10. Output filter removes harmful content and redacts PII.
11. Response is stored in cache and returned to client.

## Security Boundaries

- **Network** – TLS termination at Ingress; internal traffic on a private Kubernetes network.
- **Authentication** – Every `/api/v1/*` route requires a valid JWT.
- **Input** – Sanitized and injection-checked before reaching the LLM.
- **Output** – Safety-filtered and PII-redacted before returning to the client.
- **Container** – Non-root user, read-only root filesystem recommendation.

## Scalability Considerations

- Stateless API pods – horizontal scaling via Kubernetes HPA.
- Redis handles shared cache state across pod replicas.
- Batch processor amortises LLM API latency for burst traffic.
- Prometheus + Grafana provide observability for scaling decisions.
