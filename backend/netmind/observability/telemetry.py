from typing import Dict, Any

class TelemetryManager:
    """
    OpenTelemetry integration wrapper for NetMind.
    In a real implementation, this wraps opentelemetry-api and opentelemetry-sdk.
    """
    
    @staticmethod
    def record_backend_metric(name: str, value: float, tags: Dict[str, str] = None):
        """Record backend metrics: latency, throughput, errors, CPU, memory."""
        # Stub: send to Prometheus via OpenTelemetry Meter
        pass
        
    @staticmethod
    def record_kafka_metric(name: str, value: float, topic: str):
        """Record Kafka metrics: consumer lag, throughput, failed messages."""
        # Stub: send to Prometheus via OpenTelemetry Meter
        pass

    @staticmethod
    def record_ml_metric(name: str, value: float, model_name: str, tags: Dict[str, str] = None):
        """Record ML metrics: inference latency, prediction distribution, drift, model failures."""
        # Stub: send to Prometheus via OpenTelemetry Meter
        pass

    @staticmethod
    def record_business_metric(name: str, value: float, tags: Dict[str, str] = None):
        """
        Record Business metrics: detection time, investigation time, false positives, MTTR proxy.
        Monitoring dashboards MUST show actual measured application telemetry, never fake numbers.
        """
        # Stub: send to Prometheus via OpenTelemetry Meter
        pass

# Example of a middleware or decorator that would use this:
# @app.middleware("http")
# async def telemetry_middleware(request: Request, call_next):
#     start = time.time()
#     response = await call_next(request)
#     latency = (time.time() - start) * 1000
#     TelemetryManager.record_backend_metric("api_latency_ms", latency, {"path": request.url.path})
#     return response
