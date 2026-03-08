# 🔐 Secure & Cost-Efficient LLM Deployment

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![CI](https://img.shields.io/badge/CI-passing-brightgreen)

> A production-ready framework for deploying Large Language Models (LLMs) securely and cost-efficiently, featuring JWT authentication, prompt injection detection, PII filtering, semantic caching, smart query routing, and full observability.

---

## 🎯 Motivation

Deploying LLMs in production introduces two major challenges:

1. **Security** – LLMs are vulnerable to prompt injection, data leakage, and PII exposure.
2. **Cost** – Running large models for every request is expensive and wasteful.

This project addresses both challenges with a layered architecture that secures every request while routing queries intelligently to minimize cost.

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
     │ Batch Processor        │  │
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
│        Prometheus Metrics │ Structured Logging               │
│        Grafana Dashboards │ Alerting                         │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- 🔒 **JWT Authentication** – Stateless, token-based API security
- 🛡️ **Prompt Injection Detection** – Pattern-based guard with confidence scoring
- 🕵️ **PII Filter** – Detects & redacts emails, SSNs, credit cards, phone numbers
- 🧹 **Input Sanitization** – Strips XSS, HTML, SQL injection patterns
- 🚦 **Rate Limiting** – Per-user request throttling
- 🔀 **Smart Query Router** – Routes cheap queries to small models, complex ones to large
- ⚡ **Semantic Cache** – Redis-based cache with similarity matching (up to 40% cost savings)
- 📦 **Batch Processor** – Groups requests for throughput efficiency
- 📊 **Prometheus + Grafana** – Full observability stack
- 🐳 **Docker & Kubernetes** – Production-grade deployment manifests

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI |
| Authentication | JWT (python-jose) |
| Rate Limiting | slowapi |
| Cache | Redis + sentence-transformers |
| LLM Backends | OpenAI API / HuggingFace |
| Metrics | Prometheus + Grafana |
| Containerization | Docker / Kubernetes |
| Testing | pytest |
| CI/CD | GitHub Actions |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Redis (or use Docker Compose)

### 1. Clone & Install

```bash
git clone https://github.com/Gurutejareddy9/secure-llm-deployment.git
cd secure-llm-deployment
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set JWT_SECRET, OPENAI_API_KEY, etc.
```

### 3. Run with Docker Compose

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### 4. Run Locally (Development)

```bash
bash scripts/run_dev.sh
```

The API will be available at `http://localhost:8000`.

---

## 📡 API Usage

### Get a JWT Token

```bash
curl -X POST http://localhost:8000/api/v1/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"
```

### Query the LLM

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain transformers in 2 sentences"}'
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics

```bash
curl http://localhost:8000/metrics
```

---

## 🔐 Security Features

| Feature | Description |
|---------|-------------|
| Prompt Injection Guard | Detects 20+ known injection patterns |
| PII Redaction | Email, SSN, credit card, phone, IP masking |
| Input Sanitization | HTML/script stripping, length limits |
| Output Filtering | Harmful content detection in responses |
| JWT Auth | HS256-signed tokens with expiry |
| Rate Limiting | 60 req/min per user (configurable) |

---

## 💰 Cost Optimization Strategies

| Strategy | Estimated Savings |
|----------|------------------|
| Semantic Response Cache | 20–40% |
| Smart Query Routing (small vs large model) | 30–50% |
| Request Batching | 10–20% |
| 4-bit Model Quantization (local) | 60–75% GPU memory |

---

## 📁 Folder Structure

```
secure-llm-deployment/
├── src/                    # Application source code
│   ├── api_gateway/        # FastAPI app, routes, auth, middleware
│   ├── security/           # Input sanitizer, prompt guard, PII filter
│   ├── inference/          # LLM engine, batch processor, model loader
│   ├── routing/            # Smart query router
│   ├── cache/              # Redis semantic cache
│   └── monitoring/         # Prometheus metrics, structured logger
├── config/                 # YAML configuration files
├── docker/                 # Dockerfiles and docker-compose
├── kubernetes/             # K8s manifests
├── tests/                  # pytest test suite
├── notebooks/              # Jupyter demo notebook
├── docs/                   # Architecture, security, cost docs
└── scripts/                # Setup and benchmark scripts
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
