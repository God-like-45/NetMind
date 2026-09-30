# NetMind Architecture

> **Status:** Phase 1 implementation. This document covers both the local development
> architecture (currently implemented) and the production-scale architecture (documented
> for future implementation).

---

## Design Philosophy

1. **Modular monolith first.** All backend logic lives in one deployable unit until scaling requirements justify separation. Kafka provides decoupling between ingestion and processing without requiring separate services.

2. **No technology without justification.** Every technology in this stack has a concrete engineering reason documented below.

3. **Data contract first.** Pydantic schemas define the interface between all system components. Schema changes are versioned.

4. **Security is not an afterthought.** Authentication, authorization, audit logging, and secrets management are foundational, not optional layers.

5. **Observability from day one.** Structured JSON logging, request IDs, and health probes are present before any ML code.

---

## Local Development Architecture (Phase 1)

### Services

| Service | Image | Purpose |
|---|---|---|
| postgres | postgres:16-alpine | Application database, time-series telemetry (TimescaleDB via extension), vector store (pgvector) |
| redis | redis:7-alpine | Rate limiting counters, session store, human-approval pub/sub |
| zookeeper | confluentinc/cp-zookeeper:7.7.0 | Kafka coordination (required dependency) |
| kafka | confluentinc/cp-kafka:7.7.0 | Event bus: telemetry, alarms, topology, anomalies, incidents |
| backend | python:3.11-slim (multi-stage) | FastAPI application + ML pipelines |

Services enabled in later phases (defined in docker-compose.yml as commented stubs):
- mlflow (Phase 2)
- ollama (Phase 6)
- prometheus (Phase 9)
- grafana (Phase 9)
- frontend (Phase 8)

### Network

All services communicate on a single Docker bridge network (`netmind-network`).
All port bindings use `127.0.0.1:<host-port>:<container-port>` to prevent external exposure.

### Data Flow (Phase 1)

```
Client -> FastAPI Backend -> PostgreSQL
                          -> Redis (health probe)
```

### Data Flow (Phase 2+)

```
Synthetic Generator -> Kafka Topics
                         |
                         v
                   Kafka Consumer (ingestion worker)
                         |
                         v
                   PostgreSQL (TimescaleDB hypertables)
                         |
                         v
                   Anomaly Detection Service
                         |
                         v
                   Kafka (netmind.anomalies topic)
                         |
                         v
                   Correlation Engine -> Incident record
```

---

## Database Design

### Technology: PostgreSQL 16 with Extensions

**Why PostgreSQL (not a time-series-only database):**
- TimescaleDB extension adds native time-series hypertable compression and time-bucket aggregation
- pgvector extension adds embedding storage for RAG (Phase 5), eliminating a separate vector database service
- Relational integrity for incidents, users, audit logs
- pg_stat_statements for query monitoring
- Single database server reduces operational complexity for local development

**Why not InfluxDB or TimescaleDB Cloud:**
- Avoids vendor lock-in
- All data stays in one engine
- SQL familiarity for the full team

### Schema (Phase 1)

| Table | Purpose |
|---|---|
| `audit_log` | Immutable write-ahead log of all privileged actions |
| `users` | Application users with roles |

**Planned tables (added in phase migrations):**

| Table | Phase | Notes |
|---|---|---|
| `telemetry_raw` | 2 | TimescaleDB hypertable partitioned by time |
| `alarms` | 2 | Raw alarm events |
| `anomalies` | 2 | Detected anomalies with scores |
| `incidents` | 4 | Correlated incident records |
| `rca_hypotheses` | 4 | Ranked root cause hypotheses per incident |
| `topology_nodes` | 3 | Network element inventory |
| `topology_edges` | 3 | Network links |
| `documents` | 5 | Indexed engineering documents |
| `document_chunks` | 5 | Vector-embedded document chunks |
| `agent_sessions` | 6 | AI agent investigation sessions |
| `approval_queue` | 6 | Human-approval actions |

### Migration Strategy

Alembic with async engine. All schema changes are explicit Python migration files:
- No autogenerate-only workflow (autogenerate detects, human reviews and edits before committing)
- Each migration has a `downgrade()` function
- Migrations are numbered with timestamps for unambiguous ordering
- TimescaleDB hypertable creation is handled in Phase 2 migration

---

## API Design

### Versioning

All endpoints are versioned under `/api/v1/`. Breaking changes increment the version.
The root `/health` is unversioned (container orchestrators depend on it).

### Authentication (Phase 7)

JWT Bearer tokens with HS256 signing.
- Access tokens: 30 minutes (configurable)
- Refresh tokens: 7 days
- No token storage server-side (stateless validation)
- Revocation via Redis allowlist (implemented Phase 7)

### Authorization (Phase 7)

Role-based access control with four roles:

| Role | Capabilities |
|---|---|
| viewer | Read-only access to incidents, anomalies, topology |
| operator | viewer + acknowledge incidents, add comments |
| engineer | operator + trigger agent investigations, propose actions |
| admin | engineer + manage users, view audit log, approve actions |

### Rate Limiting

slowapi (based on limits library) with Redis backend:
- Default: 100 requests/minute per IP
- Agent endpoints: 10 requests/minute per user (LLM calls are expensive)

---

## Kafka Architecture

### Why Kafka

Telecom telemetry volume can exceed 100,000 events/second in production environments.
Kafka is chosen because:
- Producers (telemetry generators, alarm collectors) are decoupled from consumers (anomaly detection, persistence)
- Consumer groups allow horizontal scaling of processing
- Log retention enables replay for reprocessing after model updates
- Offset management gives at-least-once processing guarantees

### Topics

| Topic | Key | Value | Retention |
|---|---|---|---|
| `netmind.telemetry` | `{device_id}` | JSON telemetry sample | 24h (local), 7d (production) |
| `netmind.alarms` | `{alarm_id}` | JSON alarm event | 72h |
| `netmind.topology` | `{change_id}` | JSON topology change | 7d |
| `netmind.config_changes` | `{device_id}` | JSON config change | 30d |
| `netmind.anomalies` | `{anomaly_id}` | JSON anomaly event | 7d |
| `netmind.incidents` | `{incident_id}` | JSON incident event | 30d |

### Topic Configuration

- Replication factor: 1 (local dev), 3 (production)
- Partitions: 1 (local dev), 12 (production, matches expected consumer parallelism)
- Auto-create disabled: topics must be explicitly created by the init script

---

## ML Architecture (Phase 2+)

### Anomaly Detection

Two-stage approach:

1. **Isolation Forest (baseline)**
   - Justification: No labeled anomaly data is assumed. Isolation Forest is robust for multivariate unsupervised anomaly detection.
   - Input: 5-minute rolling window feature vector per device (mean, std, rate-of-change, Z-score for each metric)
   - Output: anomaly score [0,1], threshold configurable

2. **LSTM Autoencoder (improved)**
   - Justification: Telemetry has strong temporal structure. Reconstruction error from an LSTM captures sequence anomalies that Isolation Forest misses.
   - Input: 60-point time window (5 minutes of per-minute samples)
   - Output: reconstruction error, compared against per-device rolling baseline

### Evaluation

Models are evaluated against synthetically injected anomalies with known ground truth.
All metrics (precision, recall, F1) are labeled as **measured on synthetic data** and clearly not claimed as production performance.

### MLflow

- Experiment: `netmind-anomaly-detection`
- Each training run logs: hyperparameters, dataset version (DVC), precision, recall, F1
- Model Registry: promoted models go through staging -> production stages
- No auto-promotion: human reviews evaluation metrics before promoting

---

## Security Architecture

See [security.md](security.md) for the full security document.

Key principles:
- All secrets via environment variables
- JWT with configurable expiry
- RBAC enforced at middleware level
- Audit log for every write action
- LLM cannot execute shell commands
- Prompt injection detection on all user-supplied text
- Container runs as non-root user (uid 1001)

---

## Production Architecture (Future - Phase 10)

This section documents the intended production deployment.
**None of this is currently deployed.**

### Compute

- Kubernetes on GKE / EKS
- Backend: 3 replicas minimum, HPA on CPU and request rate
- Kafka: managed service (Confluent Cloud or MSK) - 3 broker cluster
- PostgreSQL: managed service (Cloud SQL / RDS) with read replica
- Redis: managed service (Elasticache / Memorystore)
- Ollama: separate GPU node pool for LLM inference

### Scaling Targets (assumptions, not measured results)

| Component | Target | Basis |
|---|---|---|
| Telemetry ingestion | 50,000 events/sec | Assumption based on typical medium carrier NOC |
| API latency (p99) | < 200ms | Target, not measured |
| Anomaly detection latency | < 30 seconds from event | Target |
| RAG retrieval | < 2 seconds | Target |
| Agent investigation | < 60 seconds | Target |

All targets above are **design targets**, not measured results.

### Disaster Recovery

- PostgreSQL: daily snapshots + WAL archiving, point-in-time recovery
- Kafka: topic replication factor 3, cross-AZ brokers
- Model artifacts: DVC + cloud storage (GCS/S3)
- RTO target: 4 hours (assumption)
- RPO target: 1 hour (assumption)
