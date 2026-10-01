# NetMind AI: 10-Minute Interview Demo Runbook

This runbook is designed for a live technical interview demonstration. It walks the interviewer through the exact capabilities of NetMind AI as they currently exist in code, proving our end-to-end architecture from Kafka ingestion to React visualization.

**Duration:** ~10 Minutes
**Pre-requisites:** Docker Compose cluster running (PostgreSQL, Redis, Kafka, FastAPI, Next.js, ML Services).

---

## Step 1: The Dashboard (System Overview)

**WHAT I CLICK:** Navigate to `http://localhost:3000/dashboard`
**WHAT HAPPENS:** The dashboard loads, displaying live metrics for Active Incidents, Open Anomalies, Devices Monitored, and Pending Approvals. The Topology map is rendered.
**WHICH API IS CALLED:** `GET /api/v1/incidents` and `GET /api/v1/devices`
**WHICH SERVICE HANDLES IT:** FastAPI `incidents.py` and `devices.py` routers.
**WHERE DATA IS STORED:** PostgreSQL (`incidents` and `devices` tables).
**WHY THE FEATURE EXISTS:** Provides the NOC (Network Operations Center) operator with an immediate, high-level view of network health without digging into logs.

## Step 2: Device Selection & Telemetry

**WHAT I CLICK:** Click on the "Devices" tab in the sidebar, then select a specific router (e.g., `router-core-01`).
**WHAT HAPPENS:** The device details page opens. You see recent telemetry streams (CPU, memory, interface errors, BGP flaps).
**WHICH API IS CALLED:** `GET /api/v1/network/devices/{id}` and `GET /api/v1/network/telemetry?device_id={id}`
**WHICH SERVICE HANDLES IT:** FastAPI `network.py` router fetching historical metrics.
**WHERE DATA IS STORED:** Ingested via Kafka (`telemetry_events` topic) and persisted in PostgreSQL.
**WHY THE FEATURE EXISTS:** Essential for investigating raw metrics surrounding an incident before trusting the ML predictions.

## Step 3: Topology Correlation

**WHAT I CLICK:** Navigate to the "Topology" tab.
**WHAT HAPPENS:** A visual map of network edges and nodes is displayed.
**WHICH API IS CALLED:** `GET /api/v1/topology`
**WHICH SERVICE HANDLES IT:** FastAPI `topology.py` router.
**WHERE DATA IS STORED:** PostgreSQL (`topology_nodes` and `topology_edges` tables).
**WHY THE FEATURE EXISTS:** Allows engineers to see blast radius. If a core router fails, the topology map indicates which downstream access switches are affected.

## Step 4: Incident Generation / Detection

**WHAT I CLICK:** Open the Terminal and run `python netmind/simulator/main.py --scenario bgp_flap`. Wait 5 seconds.
**WHAT HAPPENS:** The simulator generates anomalous Kafka telemetry. The `KafkaConsumerService` consumes it, the ML worker detects an anomaly, and an incident is automatically generated. The UI dashboard counter increments.
**WHICH API IS CALLED:** No frontend API yet. Kafka Producer -> Broker -> Kafka Consumer.
**WHICH SERVICE HANDLES IT:** `telemetry_worker.py` and `IsolationForestModel`.
**WHERE DATA IS STORED:** `telemetry` (PostgreSQL), `predictions` (PostgreSQL), and finally `incidents` (PostgreSQL).
**WHY THE FEATURE EXISTS:** Proves the asynchronous streaming pipeline is functional and decoupled from the synchronous web API.

## Step 5: Incident Investigation

**WHAT I CLICK:** Navigate to the "Incidents" tab and click the newly generated incident.
**WHAT HAPPENS:** The Incident Investigation page (`/incidents/[id]`) opens, showing severity, status, triggering metrics, and observed vs expected values.
**WHICH API IS CALLED:** `GET /api/v1/incidents/{id}`
**WHICH SERVICE HANDLES IT:** FastAPI `incidents.py`.
**WHERE DATA IS STORED:** PostgreSQL `incidents` table.
**WHY THE FEATURE EXISTS:** Centralizes all context for a failure so an operator does not have to pivot between 5 different tools (Grafana, Kibana, Jira, etc).

## Step 6: ML Anomaly / Prediction & Evidence

**WHAT I CLICK:** Scroll down on the Incident Investigation page to "Candidate Root Causes".
**WHAT HAPPENS:** The UI displays model-generated hypotheses (e.g., "BGP Policy Misconfiguration") along with an anomaly score and supporting evidence bullet points.
**WHICH API IS CALLED:** `GET /api/v1/incidents/{id}/root-cause`
**WHICH SERVICE HANDLES IT:** FastAPI `incidents.py` integrating with the ML prediction tables.
**WHERE DATA IS STORED:** `predictions` and `incidents` tables.
**WHY THE FEATURE EXISTS:** Reduces Mean Time To Resolution (MTTR) by pointing the engineer in the statistically most probable direction immediately.

## Step 7: Human Approval (HITL)

**WHAT I CLICK:** Type "Verified BGP config on router" in the resolution notes textarea, and click the **Approve Hypothesis** button.
**WHAT HAPPENS:** The incident status changes to RESOLVED, the human approval state is updated, and the action is logged.
**WHICH API IS CALLED:** `POST /api/v1/incidents/{id}/action` with payload `{"action": "APPROVE"}`
**WHICH SERVICE HANDLES IT:** FastAPI `incidents.py` state machine logic.
**WHERE DATA IS STORED:** Updates the `incidents` table and appends a JSON audit log.
**WHY THE FEATURE EXISTS:** Ensures ML models do not blindly act on network infrastructure without human validation (Human-In-The-Loop), mitigating risk.

## Step 8: Audit Log

**WHAT I CLICK:** Scroll to the "Investigation Timeline (Audit Trail)" section on the incident page.
**WHAT HAPPENS:** Shows a chronological timeline of when the incident was detected, when the model generated a hypothesis, and when the user approved it.
**WHICH API IS CALLED:** Rendered as part of `GET /api/v1/incidents/{id}`.
**WHICH SERVICE HANDLES IT:** FastAPI `incidents.py`.
**WHERE DATA IS STORED:** `audit_trail` JSONB column in the `incidents` table.
**WHY THE FEATURE EXISTS:** Compliance, post-mortems, and retraining data for future models.

## Step 9: Model Health

**WHAT I CLICK:** Navigate to the "Model Health" (or /predictions API).
**WHAT HAPPENS:** Displays ML inference latency, feature versions, and anomaly score distributions. 
**WHICH API IS CALLED:** `GET /api/v1/predictions`
**WHICH SERVICE HANDLES IT:** FastAPI `predictions.py`.
**WHERE DATA IS STORED:** PostgreSQL `predictions` table.
**WHY THE FEATURE EXISTS:** Allows ML engineers to detect concept drift. If 100% of telemetry is suddenly marked as anomalous, the model needs retraining.

## Step 10: System Health

**WHAT I CLICK:** Navigate back to the Dashboard "Infrastructure Health" panel or hit the Health API.
**WHAT HAPPENS:** Shows the connection status to PostgreSQL, Redis, Kafka, and the API.
**WHICH API IS CALLED:** `GET /api/v1/health`
**WHICH SERVICE HANDLES IT:** FastAPI `health.py`.
**WHERE DATA IS STORED:** In-memory ping checks to respective services.
**WHY THE FEATURE EXISTS:** Standard production readiness. If Redis goes down, the rate-limiting and idempotency fail gracefully, and this dashboard highlights the failure immediately.
