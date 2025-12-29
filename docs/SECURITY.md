# LLM Gateway - Security & Privacy

**Version:** 1.0
**Last Updated:** December 2024

---

## 1. Security Overview

The LLM Governance Gateway is designed with security-first principles to protect enterprise data while enabling LLM capabilities.

### 1.1 Security Principles

| Principle | Implementation |
|-----------|----------------|
| **Zero Trust** | Every request authenticated and authorized |
| **Defense in Depth** | Multiple security layers |
| **Least Privilege** | Minimal permissions by default |
| **Data Minimization** | Only store what's necessary |
| **Encryption Everywhere** | TLS in transit, AES at rest |

---

## 2. Data Flow Architecture

### 2.1 Request Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW DIAGRAM                                │
└──────────────────────────────────────────────────────────────────────────────┘

                                    EXTERNAL
    ┌─────────┐                                              ┌─────────────────┐
    │  Client │                                              │  LLM Provider   │
    │   App   │                                              │ (OpenAI, etc.)  │
    └────┬────┘                                              └────────▲────────┘
         │                                                            │
         │ HTTPS (TLS 1.3)                              HTTPS (TLS 1.3)
         │                                                            │
═════════╪════════════════════════════════════════════════════════════╪═════════
         │                         GATEWAY                            │
         ▼                                                            │
    ┌─────────────────────────────────────────────────────────────────┴───────┐
    │                           SECURITY LAYER                                 │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
    │  │   TLS    │  │   Auth   │  │  Input   │  │ Security │  │  Output  │  │
    │  │Termination│  │  Check   │  │Validation│  │  Guards  │  │ Filter   │  │
    │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
    └─────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                          GOVERNANCE LAYER                                │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
    │  │  Policy  │  │  Budget  │  │  Feature │  │   Rate   │                │
    │  │  Engine  │  │  Check   │  │Allowlist │  │  Limiter │                │
    │  └──────────┘  └──────────┘  └──────────┘  └──────────┘                │
    └─────────────────────────────────────────────────────────────────────────┘
                                       │
═══════════════════════════════════════╪══════════════════════════════════════
                                       │
                                  INTERNAL
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
         ▼                             ▼                             ▼
    ┌─────────┐                  ┌─────────┐                  ┌─────────┐
    │  Redis  │                  │PostgreSQL│                  │  Logs   │
    │ (Cache) │                  │(Metadata)│                  │(Metrics)│
    └─────────┘                  └─────────┘                  └─────────┘
```

### 2.2 What Flows Where

| Data Type | Destination | Encrypted | Retained |
|-----------|-------------|-----------|----------|
| Prompts/Messages | LLM Provider | Yes (TLS) | **NO** |
| LLM Responses | Client only | Yes (TLS) | **NO** |
| API Keys (hashed) | PostgreSQL | Yes (AES) | Yes |
| Usage Metadata | PostgreSQL | Yes (AES) | Yes |
| Rate Limit Counters | Redis | Yes (TLS) | Temporary |
| Audit Events | PostgreSQL | Yes (AES) | Configurable |

---

## 3. Data Storage Policy

### 3.1 What We Store

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA STORED IN GATEWAY                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ STORED (Encrypted)                                          │
│  ────────────────────                                           │
│  • API key hashes (SHA-256, salted)                             │
│  • Organization/tenant metadata                                  │
│  • Application configurations                                    │
│  • Policy definitions                                           │
│  • Budget configurations and usage counters                     │
│  • Feature allowlist definitions                                │
│  • Audit log metadata:                                          │
│    - Timestamp                                                  │
│    - Request ID                                                 │
│    - App ID                                                     │
│    - Model used                                                 │
│    - Token counts                                               │
│    - Cost                                                       │
│    - Decision outcome                                           │
│    - Latency                                                    │
│                                                                  │
│  ⏱️ TEMPORARY (Redis, TTL-based)                                │
│  ────────────────────────────────                               │
│  • Rate limit counters (expires after window)                   │
│  • Session tokens (configurable TTL)                            │
│  • Cached policy decisions (short TTL)                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 What We DO NOT Store

```
┌─────────────────────────────────────────────────────────────────┐
│               DATA NOT STORED BY GATEWAY                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ❌ NEVER STORED                                                │
│  ──────────────                                                 │
│  • Prompt content / User messages                               │
│  • LLM responses / Completions                                  │
│  • Conversation history                                         │
│  • Embeddings vectors                                           │
│  • File contents                                                │
│  • User personal data (beyond tenant metadata)                  │
│  • LLM provider API keys (passed through only)                  │
│                                                                  │
│  The gateway is a PASS-THROUGH proxy for LLM content.           │
│  Content flows: Client → Gateway → LLM → Gateway → Client       │
│  Nothing is persisted in between.                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Retention

| Data Type | Retention | Deletion |
|-----------|-----------|----------|
| Audit logs | Tier-based (7-365 days) | Automatic |
| Usage metrics | 90 days | Automatic |
| API keys | Until revoked | On request |
| Tenant data | Until deleted | On request |
| Rate limit data | Window duration | Automatic |

---

## 4. Security Controls

### 4.1 Authentication

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOW                           │
└─────────────────────────────────────────────────────────────────┘

    Request
       │
       ▼
  ┌─────────┐     ┌─────────────────────────────────────┐
  │ X-API-  │────▶│  1. Extract API key from header     │
  │  Key    │     │  2. Hash key with SHA-256           │
  │ Header  │     │  3. Lookup in database              │
  └─────────┘     │  4. Verify not expired/disabled     │
                  │  5. Load tenant context             │
                  └─────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
              ┌──────────┐                 ┌──────────┐
              │  VALID   │                 │ INVALID  │
              │   200    │                 │   401    │
              └──────────┘                 └──────────┘

API Key Format: gw_<prefix>_<random_32_chars>
Storage: SHA-256(key + salt) - original never stored
```

### 4.2 Authorization (RBAC)

| Role | Permissions |
|------|-------------|
| `viewer` | Read-only access to own resources |
| `developer` | Use API, view usage |
| `admin` | Manage apps, policies, budgets |
| `owner` | Full tenant control |

### 4.3 Input Validation

```python
# All inputs validated against strict schemas
class SecurityChecks:
    - Schema validation (Pydantic)
    - Max token limits
    - Max message count
    - Content length limits
    - Character encoding validation
```

### 4.4 Security Guards

| Guard | Detection | Action |
|-------|-----------|--------|
| **PII Detection** | Email, phone, SSN patterns | Block/Warn |
| **Prompt Injection** | Jailbreak patterns | Block |
| **Secret Detection** | API keys, passwords | Block |
| **Sensitive Topics** | Configurable blocklist | Block/Warn |
| **Instruction Leakage** | System prompt extraction | Block |

Example detection patterns:
```python
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
}

INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"disregard all prior",
    r"you are now",
    r"new persona",
]
```

---

## 5. Network Security

### 5.1 TLS Configuration

```yaml
# Minimum TLS 1.2, prefer TLS 1.3
tls:
  min_version: TLSv1.2
  prefer_version: TLSv1.3
  ciphers:
    - TLS_AES_256_GCM_SHA384
    - TLS_CHACHA20_POLY1305_SHA256
    - TLS_AES_128_GCM_SHA256
```

### 5.2 Network Isolation

```
┌─────────────────────────────────────────────────────────────────┐
│                     NETWORK ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────┘

    INTERNET                    DMZ                    PRIVATE
    ─────────                ─────────               ─────────────
        │                        │                        │
        │   ┌──────────────┐    │                        │
        └──▶│ Load Balancer│    │                        │
            │  (WAF/DDoS)  │    │                        │
            └──────┬───────┘    │                        │
                   │            │                        │
            ═══════╪════════════╪════════════════════════╪═════
                   │            │                        │
                   │    ┌───────▼───────┐               │
                   │    │   Gateway     │               │
                   │    │   Service     │               │
                   │    └───────┬───────┘               │
                   │            │                        │
            ═══════╪════════════╪════════════════════════╪═════
                   │            │                        │
                   │            │    ┌──────────────────┐│
                   │            └───▶│ Redis / Postgres ││
                   │                 │  (Private only)  ││
                   │                 └──────────────────┘│
                   │                                     │
                   │            ┌──────────────────┐    │
                   └───────────▶│  LLM Providers   │    │
                                │  (Outbound only) │    │
                                └──────────────────┘    │

Firewall Rules:
- Inbound: HTTPS (443) only through LB
- Internal: Gateway → Redis (6379), PostgreSQL (5432)
- Outbound: Gateway → LLM APIs (443)
```

### 5.3 Rate Limiting & DDoS Protection

| Layer | Protection |
|-------|------------|
| Edge (CDN/LB) | DDoS mitigation, WAF |
| Gateway | Per-key rate limits |
| Application | Concurrent connection limits |

---

## 6. Encryption

### 6.1 In Transit

| Connection | Encryption |
|------------|------------|
| Client → Gateway | TLS 1.3 |
| Gateway → LLM Provider | TLS 1.3 |
| Gateway → PostgreSQL | TLS 1.2+ |
| Gateway → Redis | TLS 1.2+ |

### 6.2 At Rest

| Data | Encryption |
|------|------------|
| PostgreSQL | AES-256 (RDS/Cloud SQL) |
| Redis | AES-256 (ElastiCache) |
| Backups | AES-256 |
| API Keys | SHA-256 + Salt (hashed, not encrypted) |

---

## 7. Audit & Compliance

### 7.1 Audit Log Contents

```json
{
  "event_id": "evt_abc123",
  "timestamp": "2024-12-14T10:30:00Z",
  "event_type": "llm_request",
  "app_id": "app_xyz",
  "tenant_id": "tenant_123",
  "request_id": "req_456",
  "model": "gpt-4o",
  "tokens": {
    "prompt": 150,
    "completion": 200,
    "total": 350
  },
  "cost_usd": 0.0105,
  "latency_ms": 1250,
  "decision": {
    "outcome": "allow",
    "checks_passed": ["auth", "policy", "budget", "security"]
  },
  "ip_address": "192.168.1.100",
  "user_agent": "MyApp/1.0"
}
```

**Note:** Prompt content and LLM responses are NOT included in audit logs.

### 7.2 Compliance Standards

| Standard | Status | Notes |
|----------|--------|-------|
| SOC 2 Type II | In Progress | Expected Q2 2025 |
| GDPR | Compliant | EU data residency available |
| CCPA | Compliant | Data deletion on request |
| HIPAA | Roadmap | Contact for BAA |

### 7.3 Data Residency

| Region | Available | Data Center |
|--------|-----------|-------------|
| US | Yes | AWS us-east-1, us-west-2 |
| EU | Yes | AWS eu-west-1, eu-central-1 |
| APAC | Roadmap | AWS ap-southeast-1 |

---

## 8. Incident Response

### 8.1 Security Incident Classification

| Severity | Description | Response Time |
|----------|-------------|---------------|
| Critical | Data breach, system compromise | Immediate |
| High | Unauthorized access attempt | 1 hour |
| Medium | Policy violation | 4 hours |
| Low | Anomaly detected | 24 hours |

### 8.2 Incident Response Process

```
1. DETECT    → Automated monitoring alerts
2. TRIAGE    → Security team assessment
3. CONTAIN   → Isolate affected systems
4. ERADICATE → Remove threat
5. RECOVER   → Restore services
6. REVIEW    → Post-incident analysis
```

### 8.3 Security Contact

- **Security Issues:** security@your-domain.com
- **Bug Bounty:** Coming soon
- **PGP Key:** Available on request

---

## 9. Security Best Practices for Clients

### 9.1 API Key Management

```python
# DO: Use environment variables
import os
api_key = os.environ["GATEWAY_API_KEY"]

# DO: Rotate keys regularly
# Recommended: Every 90 days

# DON'T: Hardcode keys
api_key = "gw_xxx_hardcoded"  # NEVER DO THIS

# DON'T: Commit keys to git
# Use .gitignore and secret managers
```

### 9.2 Request Security

```python
# DO: Use HTTPS only
client = GatewayClient("https://api.gateway.com")

# DO: Validate responses
response = client.chat(...)
if response.status != "success":
    handle_error(response)

# DO: Implement retry with backoff
from tenacity import retry, wait_exponential

@retry(wait=wait_exponential(multiplier=1, max=60))
def call_llm():
    return client.chat(...)
```

### 9.3 Data Handling

```python
# DO: Sanitize inputs before sending
def sanitize_prompt(text: str) -> str:
    # Remove potential PII
    # Remove injection patterns
    return cleaned_text

# DO: Use features/contracts
request = {
    "contract": {
        "app_id": "my-app",
        "feature": "customer-support",  # Tracked
        "action": "generate"
    }
}
```

---

## 10. Privacy Statement

### 10.1 Data Controller

The organization deploying the LLM Gateway is the data controller. Anthropic/OpenAI remain data processors for LLM inference.

### 10.2 Data Processing

| Purpose | Legal Basis | Data |
|---------|-------------|------|
| Authentication | Contract | API keys, tenant info |
| Authorization | Contract | Policies, permissions |
| Usage tracking | Legitimate interest | Metadata, costs |
| Security | Legitimate interest | IP, patterns |

### 10.3 Data Subject Rights

| Right | Supported | How |
|-------|-----------|-----|
| Access | Yes | API or request |
| Rectification | Yes | Admin API |
| Erasure | Yes | Tenant deletion |
| Portability | Yes | Export API |
| Objection | N/A | No profiling |

### 10.4 Sub-processors

| Provider | Purpose | Location |
|----------|---------|----------|
| AWS/GCP/Azure | Infrastructure | Configurable |
| OpenAI | LLM inference | US |
| Anthropic | LLM inference | US |
| Datadog (optional) | Monitoring | US/EU |

---

## 11. Security Checklist

### For Deployment

- [ ] TLS certificates configured
- [ ] Database encryption enabled
- [ ] Redis encryption enabled
- [ ] API keys generated securely
- [ ] Rate limits configured
- [ ] Security guards enabled
- [ ] Audit logging enabled
- [ ] Backup encryption verified
- [ ] Network firewall rules applied
- [ ] Monitoring alerts configured

### For Operations

- [ ] Regular key rotation (90 days)
- [ ] Audit log review (weekly)
- [ ] Access review (quarterly)
- [ ] Penetration testing (annually)
- [ ] Dependency updates (monthly)
- [ ] Incident response drill (annually)
