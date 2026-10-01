# NETMIND

**Autonomous Telecom Network Intelligence and Incident Resolution Platform**

NetMind is an event-driven AI platform designed to automate incident resolution in telecom networks. It uses streaming telemetry and machine learning to detect anomalies in real-time, and a LangGraph-based AI agent to investigate root causes using RAG against historical engineering runbooks.

> **Implementation Status:** Fully Complete (Phases 1-6)

---

## 🎯 The Problem

Telecom network operations teams face:
- High-volume alarm streams with significant noise (alarm storms).
- Manual root cause analysis that is slow and error-prone.
- Institutional knowledge trapped in runbooks and engineering documents.
- Long mean-time-to-resolution (MTTR) due to manual investigation steps.

## ✨ The Solution (NetMind)

NetMind addresses these problems through a highly scalable, automated pipeline:
1. **Streaming Telemetry Ingestion:** Continuously ingests network telemetry from network elements using Apache Kafka.
2. **Automated Anomaly Detection:** Detects statistical anomalies in time-series metrics (CPU, memory) in real-time.
3. **AI Root Cause Analysis:** Triggers a LangGraph AI Agent to reason over events, network topology, and configuration changes.
4. **Retrieval-Augmented Generation (RAG):** The agent securely queries a Qdrant vector database to retrieve historical engineering runbooks to guide its investigation.
5. **Human-in-the-Loop Approvals:** The AI generates an evidence-backed recommendation, requiring human operator approval for any privileged remediation actions.

---

## 🏗️ System Architecture

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                          NetMind Platform                                 │
├─────────────────────────────┬─────────────────────────────────────────────┤
│   Frontend (Next.js 14)     │          API (FastAPI)                      │
│   - Dashboard               │          - REST Endpoints                   │
│   - Incident Management     │          - PostgreSQL ORM (SQLAlchemy)      │
│   - Topology Viewer         │          - RAG Queries                      │
│   - Approval Queue          │          - Human-in-the-Loop Actions        │
├─────────────────────────────┴─────────────────────────────────────────────┤
│                        Core Event-Driven Workers                          │
│                                                                           │
│  Telemetry Generator ──> Kafka (telemetry) ──> Anomaly Detection          │
│                                                       │                   │
│                                                       v                   │
│  Remediation <── Human Approval <── AI Agent <── Kafka (incidents)        │
│                                    (LangGraph)                            │
├───────────────────────────────────────────────────────────────────────────┤
│                         Data & AI Layer                                   │
│                                                                           │
│  PostgreSQL           Ollama              Qdrant              Kafka       │
│  (Relational state,   (Local LLM          (Vector DB          (Message    │
│  incidents, metrics)  inference via       for historical      Broker)     │
│                       Llama 3.2 3b)       runbook RAG)                    │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| **Backend API** | FastAPI, Python 3.11 | High performance, async-native, built-in OpenAPI schema generation. |
| **Message Broker** | Apache Kafka | Decouples telemetry ingestion from processing, handles high-throughput telecom data. |
| **Database** | PostgreSQL 16 | ACID-compliant relational storage for topology, telemetry metadata, and incident state. |
| **Vector DB (RAG)** | Qdrant | Fast, scalable similarity search for embedding and retrieving historical runbooks. |
| **AI Agent** | LangGraph, Ollama | Deterministic state-machine workflow for AI investigation; runs entirely locally using `llama3.2:3b`. |
| **Frontend UI** | Next.js 14, React | Modern, responsive dashboard with real-time state polling and clean UI aesthetics. |
| **Infrastructure** | Docker Compose | Containerized architecture for seamless local deployment and networking. |

---

## 🚀 Setup & Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 1. Start Infrastructure
```bash
# Start Postgres, Kafka, Zookeeper, Qdrant, and Ollama
docker-compose up -d
```

### 2. Prepare AI Models
```bash
# Pull the Llama model for local inference
docker exec -it netmind-ollama ollama pull llama3.2:3b
```

### 3. Start Backend & Workers
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations and seed RAG
python scripts/seed_rag.py

# Start API
uvicorn netmind.api.main:app --host 0.0.0.0 --port 8001

# Start Background Workers (in separate terminals)
python -m netmind.workers.telemetry_worker
python -m netmind.workers.incident_worker
```

### 4. Start Telemetry Generator
```bash
# Generates synthetic network telemetry and anomalies to Kafka
python data/synthetic/generator.py
```

### 5. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 📝 Implementation Phases (Complete)

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Foundation, FastAPI, PostgreSQL, Docker | ✅ Complete |
| Phase 2 | Data ingestion, Kafka, synthetic telemetry, anomaly detection | ✅ Complete |
| Phase 3 | Topology graph, blast radius, Graph ML | ✅ Complete |
| Phase 4 | AI Root Cause Analysis (LangGraph/Ollama) | ✅ Complete |
| Phase 5 | RAG Engine, Runbook document retrieval (Qdrant) | ✅ Complete |
| Phase 6 | Human-in-the-loop Remediation & Approval UI | ✅ Complete |
| Phase 7 | Authentication & Role-Based Access Control (RBAC) | ✅ Complete |

---

## 🔐 Security & Operations

- **Human-in-the-Loop:** The AI cannot autonomously execute config changes. It surfaces a confidence score and explicitly requests human approval (`MITIGATED` state) for zero-trust compliance.
- **Air-Gapped LLM:** Inference runs locally via Ollama, ensuring proprietary network topology and incidents never leave the VPC.

## 📄 License
MIT License. See LICENSE file.
