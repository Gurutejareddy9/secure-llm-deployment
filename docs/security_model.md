# Security Model & Threat Analysis

## Threat Model (STRIDE)

| Threat | Description | Mitigation |
|--------|-------------|------------|
| **Spoofing** | Attacker impersonates a valid user | JWT authentication; bcrypt password hashing |
| **Tampering** | Attacker modifies requests in transit | TLS/HTTPS; request signing recommendations |
| **Repudiation** | Denial of malicious actions | Structured logging with request IDs; audit trails |
| **Information Disclosure** | PII or model internals leaked | PII filter on inputs and outputs; system prompt protection |
| **Denial of Service** | Flood of API requests | Rate limiting (60 req/min); Kubernetes HPA |
| **Elevation of Privilege** | Prompt injection to override model behaviour | Prompt Guard with 20+ injection patterns |

---

## Attack Vectors & Mitigations

### 1. Prompt Injection

**Vector** – An attacker embeds instructions like *"ignore previous instructions"* to override the LLM's system context.

**Mitigation** – `PromptGuard` scans inputs with 20+ compiled regex patterns covering:
- Direct instruction overrides
- Role/system-prompt hijacking
- Token/delimiter smuggling
- Classic jailbreak keywords

Queries scoring above the confidence threshold (default 0.5) are blocked and logged.

---

### 2. PII Exfiltration

**Vector** – User inputs containing email addresses, SSNs, or credit card numbers that get stored in logs or passed to third-party APIs.

**Mitigation** – `PIIFilter` detects and redacts PII in **both input and output** using validated regex patterns.  Redaction modes: replace, mask, or remove.

---

### 3. Cross-Site Scripting (XSS) via Input

**Vector** – Malicious HTML/JavaScript injected into LLM prompts, potentially affecting downstream rendering.

**Mitigation** – `InputSanitizer` uses the `bleach` library to strip all HTML tags and sanitise input before processing.

---

### 4. SQL / Command Injection

**Vector** – Attempts to embed SQL or shell commands in queries.

**Mitigation** – `InputSanitizer` checks for common SQL patterns (`DROP TABLE`, `SELECT * FROM`, etc.) and rejects matching inputs.

---

### 5. Denial of Service

**Vector** – Flooding the API with requests to exhaust rate limits or incur excessive LLM API costs.

**Mitigation** – `slowapi` rate limiter enforces 60 requests/minute per IP.  Kubernetes HPA auto-scales pods.  Semantic caching reduces LLM calls.

---

### 6. Token Theft / Replay

**Vector** – Stolen JWT tokens used to impersonate a user.

**Mitigation** – Tokens expire after 24 hours.  HTTPS prevents interception.  Future: token revocation list with Redis.

---

## Security Controls by Layer

| Layer | Controls |
|-------|----------|
| Network | TLS/HTTPS, Kubernetes network policies, Ingress TLS termination |
| API Gateway | JWT authentication, Rate limiting, CORS policy |
| Input Pipeline | HTML sanitization, Length validation, SQL pattern blocking, Prompt injection detection |
| PII | Input and output PII redaction (email, SSN, credit card, phone, IP) |
| Output | Harmful-content filter, PII redaction on LLM responses |
| Container | Non-root user (UID 1000), minimal base image (python:3.11-slim) |
| Kubernetes | Resource limits, non-root security context, Secrets for sensitive values |

---

## Compliance Considerations

### GDPR
- PII is detected and redacted before logging or caching.
- Redis TTL ensures cached data is not retained indefinitely.
- Request IDs enable traceability for data subject requests.

### HIPAA
- PHI detection can be extended by adding medical identifier patterns to `PIIFilter`.
- Audit logging via structured JSON logs satisfies HIPAA audit control requirements.
- Encryption at rest for Redis volumes recommended.

### SOC 2
- Structured logging provides availability and confidentiality evidence.
- Rate limiting and HPA address availability requirements.
- Security scan CI workflow (bandit + safety) demonstrates ongoing risk management.
