# NetMind Security Architecture

> This document describes the security design of NetMind.
> Sections marked [Phase N] are planned but not yet implemented.

---

## Principles

1. **Least privilege.** Every component has the minimum permissions required for its function.
2. **Defense in depth.** Multiple layers of controls - authentication, authorization, rate limiting, audit logging.
3. **No secrets in code.** All credentials via environment variables. Pre-commit hook detects committed secrets.
4. **Auditability.** Every privileged write action produces an audit record. Audit records are immutable.
5. **Human-in-the-loop.** The AI agent cannot execute network changes. All actions require human approval.
6. **Prompt injection protection.** All user-supplied text passed to the LLM is validated and sanitized.
7. **Container security.** Application runs as non-root user (uid 1001). Ports bound to loopback in local dev.

---

## Authentication [Phase 7]

**Implementation:** JWT Bearer tokens with HS256 signing.

Token lifecycle:
- Access token: 30 minutes (configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh token: 7 days (configurable via `JWT_REFRESH_TOKEN_EXPIRE_DAYS`)
- No server-side token storage (stateless validation)
- Revocation via Redis allowlist (tokens added on logout)

Password handling:
- bcrypt hashing with cost factor 12
- Passwords never logged, never stored in plaintext
- Password change invalidates all existing tokens

---

## Authorization [Phase 7]

Role-Based Access Control (RBAC) with four roles:

| Role | Permissions |
|---|---|
| `viewer` | GET on all read endpoints |
| `operator` | viewer + acknowledge incidents, add comments |
| `engineer` | operator + trigger investigations, propose remediation |
| `admin` | engineer + manage users, view full audit log, approve privileged actions |

RBAC is enforced at the middleware layer. Every endpoint declares its minimum required role.
Authorization failures return 403 with audit log entry.

---

## Rate Limiting [Phase 1 - partially implemented]

slowapi with Redis backend:
- Default: 100 requests/minute per IP address
- Agent endpoints: 10 requests/minute per authenticated user (LLM calls are expensive and abuse vectors)
- Auth endpoints: 5 requests/minute per IP (brute force protection)

Rate limit exceeded returns HTTP 429.

---

## Secrets Management

**Current (Phase 1):**
- All secrets via environment variables
- `.env` file is gitignored - `.env.example` contains only placeholders
- Pre-commit hook (gitleaks) detects accidental secret commits
- Docker Compose reads secrets from environment at runtime

**Production (Phase 10):**
- Kubernetes Secrets or HashiCorp Vault
- Secrets injected at pod startup, not in container image
- Rotation procedures documented in RUNBOOK.md

---

## API Security

### Input Validation
- All request bodies validated by Pydantic with strict mode
- Request size limits via uvicorn configuration
- SQL injection prevention via SQLAlchemy ORM (parameterized queries only)

### Response Security
Security headers added to every response (see `netmind/app.py`):
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security` (production only)

### CORS
- Configured allowlist (not wildcard)
- Credentials allowed only for listed origins
- Configurable via `API_CORS_ORIGINS` environment variable

---

## Audit Logging

Every privileged action writes to the `audit_log` table with:
- `actor_id`: authenticated user ID
- `actor_role`: role at time of action
- `action`: action name (e.g., `INCIDENT_ACKNOWLEDGE`, `AGENT_ACTION_APPROVE`)
- `resource_type`: type of resource affected
- `resource_id`: specific resource identifier
- `request_id`: correlates with HTTP request logs
- `ip_address`: source IP
- `status`: `SUCCESS` or `FAILURE`
- `detail`: human-readable description

Audit records are never updated or deleted. The audit table is append-only.

---

## AI Agent Security [Phase 6]

### Tool Permission Boundaries

Each agent tool has a strict typed schema:
- `query_telemetry`: read-only, max time range 7 days
- `get_topology`: read-only
- `search_docs`: read-only, max k=10 results
- `get_rca`: read-only
- `propose_action`: write, requires human approval before execution

### Prompt Injection Protection

All user-supplied text is validated before being incorporated into agent prompts:
- Length limits
- Disallowed pattern detection (injection attempts like "ignore previous instructions")
- Content sanitization

Violations are logged and return `PromptInjectionError` (HTTP 400).

### What the LLM Cannot Do

The LLM is given tools with explicit schemas. It cannot:
- Execute arbitrary shell commands
- Make HTTP requests to arbitrary URLs
- Directly modify database records
- Approve its own proposed actions

All tool calls are validated against schemas before execution.

---

## Container Security

- Base image: `python:3.11-slim` (minimal attack surface)
- Application user: `netmind` (uid 1001, non-root)
- No unnecessary packages in runtime image
- Build secrets not present in runtime image (multi-stage build)
- Port bindings: `127.0.0.1` only in docker-compose.yml

---

## Known Limitations (Phase 1)

- Authentication endpoints not yet implemented (Phase 7)
- All endpoints are currently unauthenticated in the Phase 1 scaffold
- Rate limiting is configured but Redis dependency may not be available in all test scenarios
- Audit log is defined but not yet written to automatically by all services

These limitations are intentional for the phased build. Phase 7 addresses all of them.
