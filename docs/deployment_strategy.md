# NetMind Deployment & DevOps Strategy

This document outlines the strategy for deploying the NetMind platform in a realistic production environment.

## 1. Rolling Deployment & Canary Deployments

- **Rolling Deployments (Default)**: Kubernetes handles rolling updates natively. When pushing a new tag, K8s terminates pods progressively based on readiness and liveness probes ensuring zero-downtime.
- **Canary Deployments**: For heavy ML model changes or RAG pipeline shifts, we employ Argo Rollouts or Istio. 
  - 10% of API traffic is routed to the canary backend.
  - Telemetry (Prometheus) measures 500s and latency over 15 minutes.
  - If no regression is detected, traffic shifts to 100%.

## 2. Database Migration Strategy

Database migrations (Alembic) run **independently** from application startup in production.
- **Pre-Rollout Job**: A Kubernetes Job (`helm pre-upgrade` hook) executes `alembic upgrade head`.
- **Backward Compatibility**: All migrations must be backward-compatible (no dropping columns if the previous version still relies on them). 
- **Rollback**: To rollback a migration, a fix forward strategy is preferred over down-migrations in production to prevent data loss.

## 3. Rollback Mechanisms

- **Application Rollback**: Using `kubectl rollout undo deployment/netmind-backend` in case of severe bugs.
- **Model Rollback**: Handled via MLflow Model Registry. If a promoted model (e.g. `v3`) starts missing thresholds (detectable via our MLOps LLMOpsTracker), an engineer aliases `v2` as `@champion`. The backend dynamically reloads the correct model.

## 4. Configuration Versioning

- **Application Secrets**: Stored in AWS Secrets Manager and fetched into the cluster via External Secrets Operator (ESO). Secrets are NEVER in plaintext inside the YAMLs.
- **Environment Variables**: Maintained in `k8s/config.yaml` and deployed via GitOps (ArgoCD or Flux).

## 5. Security & Observability

- **Non-Root Containers**: Dockerfiles drop privileges via `USER netmind`.
- **Security Scans**: Trivy runs on every commit in GitHub Actions to block vulnerable dependencies.
- **Telemetry**: OpenTelemetry pipelines ship metrics (latency, LLM cost, worker throughput) directly to Prometheus/Grafana.
