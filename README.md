# 🔐 Secure & Cost-Efficient LLM Deployment

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

> A production-ready gateway for deploying Large Language Models with JWT authentication, prompt injection detection, PII filtering, semantic caching, smart query routing, and a live demo dashboard.

---

## 🎯 Overview

Deploying LLMs in production introduces two major challenges:

1. **Security** – LLMs are vulnerable to prompt injection, data leakage, and PII exposure.
2. **Cost** – Running large models for every request is expensive and wasteful.

This project addresses both with a layered security pipeline and intelligent cost optimization — all accessible through a single interactive dashboard.

---

## 🖥️ Live Dashboard

Open **http://localhost:8000** after starting the app to access the dashboard:

| Section | What It Shows |
|---------|---------------|
| **Stats Bar** | Total requests, cache hits, security blocks, cost, tokens, cache hit rate (auto-refreshes) |
| **Pipeline Visualization** | Animated step-by-step flow through Auth → Sanitize → Guard → PII → Cache → Route → Infer → Filter → Response |
| **Query Interface** | Send queries, see responses with model/cache/token/cost metadata |
| **Security Demos** | One-click demos: prompt injection, PII redaction, XSS, smart routing, caching, jailbreak |
| **Request Log** | Scrollable history of all queries with status |
| **Architecture Features** | Summary cards of each component |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Request                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     API Gateway (FastAPI)                     │
│   JWT Auth │ Rate Limiting │ CORS │ Request Logging          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Security Layer                            │
│  Input Sanitizer → Prompt Guard → PII Filter                │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │         Cache Layer (Redis)      │
          │   Semantic similarity lookup     │
          └────────────┬─────────┬──────────┘
                  MISS │         │ HIT
          ┌────────────▼─────┐   │
          │   Query Router   │   │
          │ Simple → Small   │   │
          │ Complex → Large  │   │
          └────────┬─────────┘   │
                   │             │
     ┌─────────────▼──────────┐  │
     │   Inference Engine     │  │
     └─────────────┬──────────┘  │
                   │             │
     ┌─────────────▼──────────┐  │
     │    Output Filter       │  │
     │ PII Check │ Safety     │  │
     └─────────────┬──────────┘  │
                   └─────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     Monitoring Stack                         │
│        Prometheus Metrics │ Structured Logging │ Dashboard   │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- 🔒 **JWT Authentication** – Stateless, token-based API security with HS256
- 🛡️ **Prompt Injection Detection** – 20+ pattern-based guards with confidence scoring
- 🕵️ **PII Filter** – Detects & redacts emails, SSNs, credit cards, phone numbers, IPs
- 🧹 **Input Sanitization** – Strips XSS, HTML, SQL injection patterns
- 🔍 **Output Filter** – Blocks harmful content (weapons, violence, drugs, self-harm)
- 🚦 **Rate Limiting** – Per-user request throttling (60 req/min default)
- 🔀 **Smart Query Router** – Routes simple queries to GPT-3.5 (cheap), complex to GPT-4
- ⚡ **Semantic Cache** – Redis + sentence-transformers with 95% similarity threshold
- 📊 **Prometheus + Grafana** – Full observability with live metrics
- 🖥️ **Interactive Dashboard** – Single-page UI to demo all features
- 🐳 **Docker Ready** – One-command deployment with Docker Compose

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI + Uvicorn |
| Authentication | JWT (python-jose) + bcrypt |
| Rate Limiting | slowapi |
| Cache | Redis + sentence-transformers |
| LLM Backends | OpenAI API (or MockEngine for testing) |
| Metrics | Prometheus + Grafana |
| Logging | structlog (JSON) |
| Security | bleach, regex pattern matching |
| Containerization | Docker Compose |
| Testing | pytest + pytest-asyncio |

---

## 🚀 Quick Start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Clone the repo

```bash
git clone https://github.com/Gurutejareddy9/secure-llm-deployment.git
cd secure-llm-deployment
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` if you want to change the JWT secret. The defaults work out of the box.

> **No OpenAI API key?** No problem — leave `OPENAI_API_KEY` empty and the app uses a **MockEngine** that returns test responses. The entire pipeline (auth, security, caching, routing, metrics) still works fully.

### 3. Start everything

```bash
docker compose -f docker/docker-compose.yml --env-file .env up --build -d
```

### 4. Open the dashboard

Visit **http://localhost:8000** in your browser. The dashboard auto-authenticates and is ready to use.

### Services started

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:8000 | Interactive demo UI |
| **API Docs** | http://localhost:8000/docs | Swagger / OpenAPI |
| **Health Check** | http://localhost:8000/health | Service status |
| **Prometheus** | http://localhost:9090 | Raw metrics |
| **Grafana** | http://localhost:3000 | Dashboards (admin/admin) |

### Stop everything

```bash
docker compose -f docker/docker-compose.yml down
```

---

## 📡 API Usage

### Get a JWT Token

```bash
curl -X POST http://localhost:8000/api/v1/token \
  -d "username=admin&password=secret"
```

Returns: `{"access_token": "eyJ...", "token_type": "bearer"}`

Default credentials: `admin` / `secret`

### Query the LLM

```bash
TOKEN=<your_token_from_above>

curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain transformers in 2 sentences"}'
```

Response:

```json
{
  "response": "...",
  "model_used": "gpt-3.5-turbo",
  "cached": false,
  "tokens_used": 145,
  "cost_usd": 0.00029
}
```

### Live Metrics (JSON)

```bash
curl http://localhost:8000/api/v1/stats
```

---

## 🔐 Security Features

| Feature | Description |
|---------|-------------|
| **Prompt Injection Guard** | Detects 20+ injection patterns (instruction override, jailbreaks, role hijacking, token smuggling) |
| **PII Redaction** | Redacts emails, SSNs, credit cards, phone numbers, IPs, DOBs in both input and output |
| **Input Sanitization** | Strips HTML/script tags, SQL patterns, non-printable characters, enforces length limits |
| **Output Filtering** | Blocks responses containing harmful content (weapons, violence, drugs, self-harm) |
| **JWT Authentication** | HS256-signed tokens with configurable 24-hour expiry |
| **Rate Limiting** | 60 requests/minute per user (configurable) |

---

## 💰 Cost Optimization

| Strategy | Estimated Savings |
|----------|------------------|
| Semantic Response Cache | 20–40% |
| Smart Query Routing (GPT-3.5 vs GPT-4) | 30–50% |
| Request Batching | 10–20% |

---

## 📁 Project Structure

```
secure-llm-deployment/
├── src/
│   ├── api_gateway/          # FastAPI app, routes, auth, middleware, dashboard
│   │   └── static/           # Dashboard HTML
│   ├── security/             # Input sanitizer, prompt guard, PII filter, output filter
│   ├── inference/            # LLM engine, batch processor, model loader
│   ├── routing/              # Smart query router
│   ├── cache/                # Redis semantic cache
│   └── monitoring/           # Prometheus metrics, structured logger
├── config/                   # YAML configuration files
├── docker/                   # Dockerfile, docker-compose.yml, prometheus.yml
├── kubernetes/               # K8s deployment manifests
├── tests/                    # pytest test suite
├── docs/                     # Architecture, security, cost analysis docs
├── scripts/                  # Setup and dev scripts
├── .env.example              # Environment template
└── requirements.txt          # Python dependencies
```

---

## 🧪 Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## 🛠️ Local Development (without Docker)

```bash
# Setup
bash scripts/setup.sh
source .venv/bin/activate

# Start Redis (required for caching)
redis-server &

# Run dev server with hot-reload
bash scripts/run_dev.sh
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -m "Add my feature"`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License – see [LICENSE](LICENSE) for details.
