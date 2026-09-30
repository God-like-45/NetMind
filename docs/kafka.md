# NetMind Kafka Architecture

## Overview

In Phase 2, we introduce Kafka as the primary ingestion and event-streaming backbone for NetMind. This ensures decoupling of the high-volume deterministic telemetry from the FastAPI control plane.

## Topics

The following topics are configured (auto-creation disabled to enforce strict schema governance):
- `telemetry.events`
- `network.alarms`
- `configuration.changes`
- `network.incidents`

## Message Schemas

We enforce strict schema validation at the ingestion layer using Pydantic models (e.g. `TelemetryEvent`, `AlarmEvent`). Kafka values are serialized as JSON payload corresponding directly to these models. 

## Partitioning Strategy & Event Key

**Event Key:** `device_id`

By using the `device_id` as the message key for all telemetry, alarms, and configuration changes originating from a specific device, we guarantee that all events for a given network element land in the same Kafka partition.

**Ordering Assumptions:** 
Because events for a single device are routed to the same partition, Kafka guarantees strict chronological ordering for that device's lifecycle. Consumers processing anomalies or state transitions will always read a device's metrics in the exact sequence they occurred.

## Producer Reliability

**Retry Behavior:**
- `retry_backoff_ms=500` ensures that transient broker failures (e.g., leader election) do not immediately drop critical network events. The producer will retry indefinitely within the configured timeout window.

**Idempotency Strategy:**
- `enable_idempotence=True`
- `acks="all"`
We utilize Kafka's built-in idempotence. This ensures that even if a producer retries a message due to a network timeout, exactly-one semantics are maintained at the broker level and no duplicate telemetry metrics or duplicate alarms are recorded in the log.
