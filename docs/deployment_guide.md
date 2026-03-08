# Deployment Guide

## Prerequisites

- Python 3.10+
- Docker 24+ and Docker Compose v2
- kubectl + a Kubernetes cluster (for K8s deployment)
- An OpenAI API key (or configure Mock mode)

---

## 1. Local Development Setup

```bash
# Clone the repository
git clone https://github.com/Gurutejareddy9/secure-llm-deployment.git
cd secure-llm-deployment

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set JWT_SECRET, OPENAI_API_KEY

# Run the development server
bash scripts/run_dev.sh
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

## 2. Docker Deployment

```bash
# Build and start all services (app + redis + prometheus + grafana)
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f app

# Stop
docker-compose -f docker/docker-compose.yml down
```

**Service URLs:**
| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin) |

---

## 3. GPU Docker Deployment

```bash
# Build GPU image
docker build -f docker/Dockerfile.gpu -t llm-gateway-gpu .

# Run with GPU support
docker run --gpus all -p 8000:8000 \
  -e JWT_SECRET=your-secret \
  -e OPENAI_API_KEY=your-key \
  llm-gateway-gpu
```

---

## 4. Kubernetes Deployment

### 4.1 Create namespace

```bash
kubectl create namespace llm-system
```

### 4.2 Create secrets

```bash
kubectl create secret generic llm-secrets \
  --namespace llm-system \
  --from-literal=jwt-secret=your-jwt-secret \
  --from-literal=openai-api-key=sk-...
```

### 4.3 Apply manifests

```bash
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/hpa.yaml
kubectl apply -f kubernetes/ingress.yaml
```

### 4.4 Verify

```bash
kubectl get pods -n llm-system
kubectl get svc -n llm-system
kubectl get hpa -n llm-system
```

---

## 5. Cloud Deployment

### AWS (EKS)
1. Create an EKS cluster with `eksctl`.
2. Install the AWS Load Balancer Controller.
3. Apply the Kubernetes manifests as above.
4. Use AWS Secrets Manager with the External Secrets Operator for secret management.

### GCP (GKE)
1. Create a GKE Autopilot cluster.
2. Use `gke-gcloud-auth-plugin` for kubectl authentication.
3. Apply the Kubernetes manifests.
4. Use Google Secret Manager with Workload Identity.

### Azure (AKS)
1. Create an AKS cluster with `az aks create`.
2. Apply the Kubernetes manifests.
3. Use Azure Key Vault with the Secrets Store CSI driver.

---

## 6. Environment Variable Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET` | Secret key for JWT signing | *required* |
| `JWT_EXPIRY_HOURS` | Token expiry duration | `24` |
| `OPENAI_API_KEY` | OpenAI API key | (uses mock if empty) |
| `REDIS_HOST` | Redis hostname | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_PASSWORD` | Redis password | (none) |
| `RATE_LIMIT_PER_MINUTE` | Max requests per minute per IP | `60` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `APP_HOST` | Bind host | `0.0.0.0` |
| `APP_PORT` | Bind port | `8000` |
| `APP_DEBUG` | Enable debug / hot reload | `false` |

---

## 7. Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v --cov=src --cov-report=html
```
