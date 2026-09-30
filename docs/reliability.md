# NetMind Reliability & Failure Recovery

This document analyzes 20 potential failure scenarios within the NetMind system, detailing their impact, mitigation, and automated recovery paths.

## 1. Kafka Failure
- **Detection**: Health check endpoint (`/health`) reports Kafka degraded; AIOKafkaProducer throws `ConnectionError`.
- **Impact**: Telemetry events cannot be ingested or published. High risk of data loss.
- **Mitigation**: Implement exponential backoff in producer.
- **Fallback**: Log events locally to disk if Kafka is unreachable.
- **Recovery**: Automatic reconnection by AIOKafka when brokers return.
- **Audit**: Log `KAFKA_DISCONNECT` audit event.
- **User Experience**: UI shows "Telemetry ingestion degraded."

## 2. PostgreSQL Failure
- **Detection**: SQLAlchemy `OperationalError`; health check degraded.
- **Impact**: Cannot read/write incidents, configuration, or agent states.
- **Mitigation**: Use `tenacity` for DB connection retries.
- **Fallback**: Circuit breaker triggers; API returns `503 Service Unavailable` cleanly rather than timing out.
- **Recovery**: Connection pooling automatically recovers when PG returns.
- **Audit**: Log `DB_FAILURE` audit event.
- **User Experience**: Graceful 503 error message in UI instead of infinite loading.

## 3. Redis Failure
- **Detection**: `redis.exceptions.ConnectionError`.
- **Impact**: Rate limiting and caching fail.
- **Mitigation**: Try-except blocks around cache GET/SET operations.
- **Fallback**: Gracefully bypass the cache (cache miss) and allow the request (fail open for rate limiting, though risky under DDoS, ensures system stays up).
- **Recovery**: Auto-reconnect.
- **Audit**: `CACHE_DEGRADED` logged.
- **User Experience**: No disruption, slightly higher latency.

## 4. Qdrant Failure
- **Detection**: `qdrant_client` raises `ResponseHandlingException`.
- **Impact**: RAG cannot fetch engineering runbooks or historical context.
- **Mitigation**: Try-except around Qdrant queries.
- **Fallback**: Return an empty context list.
- **Recovery**: Reconnect on next request.
- **Audit**: `VECTOR_DB_FAILURE` logged.
- **User Experience**: Investigation proceeds but LLM warns that historical context is unavailable.

## 5. ML Inference Failure
- **Detection**: Inference server (if external) times out, or `predict()` throws exception.
- **Impact**: Anomaly detection halts.
- **Mitigation**: Isolate ML inference in a background worker with retry logic.
- **Fallback**: Default to simple statistical thresholding (e.g., Z-score) if the ML model fails.
- **Recovery**: Worker restart.
- **Audit**: `ML_INFERENCE_FAILED` logged.
- **User Experience**: Incidents generated via statistical fallbacks tagged as "Degraded Confidence".

## 6. LLM Failure
- **Detection**: Ollama API timeout (>10s).
- **Impact**: Agent cannot plan or recommend.
- **Mitigation**: Enforce strict timeouts on LLM HTTP calls.
- **Fallback**: `KnowledgeGenerator` catches timeout and returns a hardcoded "Manual review required" fallback payload.
- **Recovery**: Next invocation tries again.
- **Audit**: `LLM_TIMEOUT` logged.
- **User Experience**: UI says "AI unavailable. Showing raw telemetry and runbook links."

## 7. Network Partition
- **Detection**: Services cannot reach each other (e.g. Backend -> DB).
- **Impact**: Split brain or service halting.
- **Mitigation**: Deploy across multiple AZs in AWS; use readiness probes.
- **Fallback**: Kubernetes routes traffic only to healthy pods in connected AZs.
- **Recovery**: Automatic upon partition heal.
- **Audit**: K8s event logs.
- **User Experience**: Momentary latency spikes.

## 8. Duplicate Events
- **Detection**: Kafka offset overlaps or duplicate IDs.
- **Impact**: Spurious incident creation.
- **Mitigation**: Redis deduplication window (e.g., hash the event ID, set TTL 5 mins).
- **Fallback**: Postgres `UNIQUE` constraint on incident signatures.
- **Recovery**: Drops duplicates silently.
- **Audit**: Drop metric incremented.
- **User Experience**: Clean incident list.

## 9. Out-of-Order Events
- **Detection**: Event timestamp < Last Processed Timestamp.
- **Impact**: False anomaly graphs.
- **Mitigation**: Time-window aggregation (tumbling windows).
- **Fallback**: Append-only TSDB stores exactly as received; query layer sorts.
- **Recovery**: N/A
- **Audit**: None required.
- **User Experience**: Graphs self-correct upon refresh.

## 10. Worker Crash
- **Detection**: Worker process exits with code > 0.
- **Impact**: Background processing halts.
- **Mitigation**: K8s Deployment `RestartPolicy=Always`.
- **Fallback**: Kafka retains messages (retention=7 days) so no data is lost.
- **Recovery**: New pod spins up and resumes from last committed offset.
- **Audit**: Pod crash logged in K8s.
- **User Experience**: Brief processing delay, no data loss.

## 11. Agent Loop
- **Detection**: LangGraph executes > `recursion_limit` steps.
- **Impact**: Infinite LLM token burning.
- **Mitigation**: Set explicit recursion limit in LangGraph compilation.
- **Fallback**: Halt execution, transition state to `WAITING_FOR_APPROVAL` with error note.
- **Recovery**: Manual intervention.
- **Audit**: `AGENT_LOOP_DETECTED`.
- **User Experience**: "Investigation halted due to complexity. Please review manually."

## 12. Malicious Prompt
- **Detection**: `llm_eval.py` detects prompt injection via heuristic or secondary model.
- **Impact**: Agent could execute harmful tools.
- **Mitigation**: Input sanitization and `is_safe_prompt` checks before LLM invocation.
- **Fallback**: Reject request with HTTP 400.
- **Recovery**: N/A
- **Audit**: `SECURITY_PROMPT_INJECTION` high-severity audit log.
- **User Experience**: "Input rejected due to security policy."

## 13. Unauthorized Tool Call
- **Detection**: Tool function checks `current_user_roles`.
- **Impact**: Privilege escalation.
- **Mitigation**: RBAC enforcement inside the tool execution layer itself.
- **Fallback**: Raise `PermissionError`, LLM receives error context.
- **Recovery**: N/A
- **Audit**: `UNAUTHORIZED_TOOL_EXECUTION`.
- **User Experience**: "You do not have permission to execute this action."

## 14. Model Drift
- **Detection**: Daily batch job evaluates current model precision against new labeled data.
- **Impact**: Rising false positive alarms.
- **Mitigation**: MLflow tracking metric alerts if AUC drops < 0.8.
- **Fallback**: Demote model to "Staging" and promote previous stable model (v-1).
- **Recovery**: Trigger automated retraining pipeline.
- **Audit**: `MODEL_DRIFT_DETECTED`.
- **User Experience**: Accuracy remains stable via champion/challenger swaps.

## 15. Schema Evolution Failure
- **Detection**: Incoming Kafka JSON fails Pydantic validation.
- **Impact**: Data dropped.
- **Mitigation**: Use Confluent Schema Registry or robust `Extra.ignore` in Pydantic.
- **Fallback**: Route malformed events to a Dead Letter Queue (DLQ).
- **Recovery**: Developer patches schema and replays DLQ.
- **Audit**: `SCHEMA_VALIDATION_FAILED`.
- **User Experience**: System continues operating on valid data.

## 16. Overloaded API
- **Detection**: High latency, 429 status codes.
- **Impact**: Service unavailable for legit users.
- **Mitigation**: Rate Limiting (`slowapi`).
- **Fallback**: Drop aggressive traffic.
- **Recovery**: Rate limit window resets.
- **Audit**: `RATE_LIMIT_EXCEEDED`.
- **User Experience**: 429 Too Many Requests response.

## 17. Database Connection Exhaustion
- **Detection**: SQLAlchemy `TimeoutError` acquiring connection from pool.
- **Impact**: All API routes fail.
- **Mitigation**: Configure `pool_size` and `max_overflow` accurately. PgBouncer integration.
- **Fallback**: Return 503 fast.
- **Recovery**: Connections return to pool once queries finish.
- **Audit**: `DB_POOL_EXHAUSTED`.
- **User Experience**: Temporary 503.

## 18. Corrupted Model Artifact
- **Detection**: `mlflow.pyfunc.load_model` fails checksum or format check.
- **Impact**: Inference crashes on startup.
- **Mitigation**: Validate artifact hash in CD pipeline before deployment.
- **Fallback**: Fallback to `default_model.pkl` baked into the Docker image.
- **Recovery**: Redeploy correct artifact.
- **Audit**: `MODEL_LOAD_FAILED`.
- **User Experience**: Uses generic baseline model temporarily.

## 19. Stale RAG Documents
- **Detection**: Document `updated_at` metadata > 90 days old.
- **Impact**: Agent suggests outdated resolutions.
- **Mitigation**: RAG ingest pipeline automatically prunes old embeddings.
- **Fallback**: LLM is instructed in prompt: "Verify if information is current before applying."
- **Recovery**: Trigger re-index from source Confluence/Git.
- **Audit**: `STALE_DOC_RETRIEVED`.
- **User Experience**: Agent flags recommendation as potentially outdated.

## 20. Incorrect Root-Cause Prediction
- **Detection**: Human operator clicks "Reject" on recommendation.
- **Impact**: Delayed MTTR.
- **Mitigation**: Capture feedback loop (thumbs down) directly into Postgres.
- **Fallback**: Agent requests human to manually identify root cause.
- **Recovery**: Nightly retraining job consumes rejected recommendations as negative samples.
- **Audit**: `RECOMMENDATION_REJECTED`.
- **User Experience**: System learns from the user's correction.
