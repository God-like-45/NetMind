# NETMIND

**Autonomous Telecom Network Intelligence and Incident Resolution Platform**

NetMind ingests network telemetry, alarms, topology data, configuration changes, and historical incidents. It detects anomalies, predicts failures, correlates events, identifies root causes, retrieves relevant engineering documentation, and performs AI-assisted investigation - with human approval required for any privileged action.

> **Implementation Status:** Phase 1 - Foundation and Backend Infrastructure
> This is an engineering project under active development. It is not production-ready.
> No production deployments exist. No fabricated benchmarks are claimed.

---

## Problem

Telecom network operations teams face:

- High-volume alarm streams with significant noise (alarm storms)
- Manual root cause analysis that is slow and error-prone
- Institutional knowledge trapped in runbooks and engineering documents
- No systematic correlation between telemetry, alarms, topology, and configuration changes
- Long mean-time-to-resolution (MTTR) due to manual investigation steps

## Product

NetMind addresses these problems by:

1. Continuously ingesting telemetry from all network elements
2. Detecting statistical anomalies in time-series metrics (CPU, memory, interface utilization, latency, packet loss)
3. Correlating related events across time and topology
4. Computing blast radius - which services and devices are affected
5. Retrieving relevant runbooks and RFCs via retrieval-augmented generation
6. Running an AI investigation agent that reasons over evidence
7. Presenting ranked root cause hypotheses with supporting evidence
8. Requiring human approval for any suggested remediation action
9. Maintaining a complete audit trail of every decision

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          NetMind Platform                                 │
├─────────────────────────────┬─────────────────────────────────────────────┤
│   Frontend (Next.js 14)     │          API (FastAPI)                      │
│   - Dashboard               │          - REST + WebSocket                 │
│   - Incident Management     │          - JWT Auth + RBAC                  │
│   - Topology Viewer         │          - Rate Limiting                    │
│   - Approval Queue          │          - Audit Logging                    │
├─────────────────────────────┴─────────────────────────────────────────────┤
│                        Core Services                                      │
│                                                                           │
│  Ingestion Service   Anomaly Detection    Correlation Engine              │
│  (Kafka consumers)   (Isolation Forest    (Time-window event              │
│                      + LSTM Autoencoder)   correlation + causal graph)    │
│                                                                           │
│  RAG Engine          AI Agent             Recommendation Engine           │
│  (LlamaIndex +       (LangGraph +         (Evidence-backed                │
│  pgvector)           Ollama)              action proposals)               │
├───────────────────────────────────────────────────────────────────────────┤
│                         Data Layer                                        │
│                                                                           │
│  PostgreSQL           Redis               Kafka                           │
│  (TimescaleDB         (Session store,     (Event bus for                  │
│  for telemetry,       rate limiting,      telemetry, alarms,              │
│  pgvector for RAG)    approval queue)     anomalies, incidents)           │
│                                                                           │
│  MLflow               DVC                                                 │
│  (Experiment          (Model + data                                       │
│  tracking)            versioning)                                         │
└───────────────────────────────────────────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for the full architecture document including production deployment design.

---

## Repository Layout

```
netmind/
├── backend/                  FastAPI application and ML pipelines
│   ├── netmind/
│   │   ├── api/              HTTP endpoints and middleware
│   │   ├── core/             Config, logging, exceptions
│   │   ├── db/               SQLAlchemy, Alembic migrations
│   │   ├── models/           ORM models
│   │   ├── schemas/          Pydantic schemas
│   │   ├── services/         Business logic
│   │   └── workers/          Kafka consumers (Phase 2+)
│   └── tests/
│       ├── unit/             No-infrastructure tests
│       └── integration/      Testcontainers-based tests (Phase 2+)
├── ml/                       ML model training code (Phase 2+)
├── pipelines/                Ingestion and processing pipelines (Phase 2+)
├── agents/                   LangGraph agent definitions (Phase 6+)
├── rag/                      RAG engine and document pipelines (Phase 5+)
├── frontend/                 Next.js 14 application (Phase 8+)
├── monitoring/               Prometheus + Grafana config (Phase 9+)
├── docker/                   Infrastructure init scripts
├── docs/                     Architecture and development documentation
├── notebooks/                Analysis notebooks (Phase 2+)
├── configs/                  Environment-specific configuration
├── data/
│   ├── synthetic/            Synthetic data generators (Phase 2+)
│   └── schemas/              Data contract schemas
├── .github/workflows/        CI pipeline
├── docker-compose.yml        Local development stack
├── Makefile                  Development commands
└── .env.example              Environment template
```

---

## Prerequisites

- Docker 24+ and Docker Compose v2
- Python 3.11+ (for local backend development)
- Node.js 20+ (for local frontend development)
- Git

---

## Local Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd netmind

# 2. Copy environment template and configure
cp .env.example .env
# Edit .env - set POSTGRES_PASSWORD, REDIS_PASSWORD, JWT_SECRET_KEY

# Generate a JWT secret:
python3 -c "import secrets; print(secrets.token_hex(32))"

# 3. Start the infrastructure
docker compose up -d

# 4. Verify services are healthy
docker compose ps

# 5. Run database migrations
make db-migrate

# 6. Verify the API is running
curl http://localhost:8000/health
```

---

## Development Commands

```bash
make help               # List all available commands

# Docker services
make dev-up             # Start all services
make dev-down           # Stop services
make dev-logs           # Stream all logs
make dev-logs-backend   # Backend logs only
make dev-status         # Show container health

# Backend
make backend-install    # Install Python dependencies
make backend-test       # Run unit tests
make backend-lint       # Lint with ruff
make backend-format     # Auto-format with ruff
make backend-typecheck  # Type check with mypy

# Database
make db-migrate         # Apply migrations
make db-rollback        # Roll back last migration
make db-shell           # Open psql shell
make db-revision MSG="description"  # Create new migration

# Frontend
make frontend-install   # Install npm packages
make frontend-dev       # Start Next.js dev server
make frontend-build     # Build production bundle

# Utilities
make generate-secret    # Generate JWT secret
make clean              # Remove Python cache files
```

---

## Implementation Status

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Foundation, FastAPI, PostgreSQL, Docker | **In Progress** |
| Phase 2 | Data ingestion, Kafka, synthetic telemetry, anomaly detection | Not started |
| Phase 3 | Topology graph, blast radius, Graph ML | Not started |
| Phase 4 | Event correlation, root cause analysis | Not started |
| Phase 5 | RAG engine, document retrieval | Not started |
| Phase 6 | AI investigation agent | Not started |
| Phase 7 | Auth, RBAC, security hardening | Not started |
| Phase 8 | Next.js frontend | Not started |
| Phase 9 | Observability, MLOps | Not started |
| Phase 10 | CI/CD complete, production architecture | Not started |

---

## Technology Decisions

Each technology is chosen for a concrete reason. See [docs/architecture.md](docs/architecture.md) for the full justification register.

| Technology | Reason |
|---|---|
| FastAPI | Async-native, OpenAPI generation, Pydantic v2, standard for ML-serving backends |
| PostgreSQL + TimescaleDB | TimescaleDB hypertables for time-series telemetry; SQL for relational data |
| Redis | Rate limiting, session store, human-approval pub/sub queue |
| Kafka | Decouples ingestion from processing; supports replay; enables event sourcing |
| Isolation Forest | Unsupervised anomaly detection - no labeled anomaly data assumed available |
| LSTM Autoencoder | Captures temporal structure in telemetry for reconstruction-error anomaly scoring |
| LangGraph | Explicit auditable agent state machine with human-in-the-loop gates |
| Ollama | Local LLM - no external API key required, air-gap compatible |

---

## Security

- JWT authentication with configurable expiry
- RBAC with four roles: viewer, operator, engineer, admin
- All secrets via environment variables (never hardcoded)
- Ports bound to 127.0.0.1 in local Docker Compose
- Audit log for every privileged action
- Rate limiting on all API endpoints
- Prompt injection detection on agent inputs
- LLM cannot directly execute shell commands or production actions

See [docs/security.md](docs/security.md) for the full security architecture.

---

## Limitations (Phase 1)

- No real network telemetry data is available. Phase 2 will implement a synthetic telemetry generator with documented statistical properties.
- No ML models are trained yet. Phase 2 implements the first anomaly detection pipeline.
- The AI agent (Phase 6) is not implemented. The RAG engine (Phase 5) is not implemented.
- Kafka topics are defined but consumers are not implemented until Phase 2.
- Authentication endpoints are defined but not implemented until Phase 7.
- Frontend is a shell until Phase 8.
- No production deployment configuration exists. Production architecture is documented in docs/architecture.md.

---

## License

MIT License. See LICENSE file.
