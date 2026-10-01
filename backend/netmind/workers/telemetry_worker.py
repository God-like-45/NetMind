import asyncio
import json
import logging
import os
import uuid
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from dotenv import load_dotenv

# Force localhost for DB when running on host BEFORE loading imports that read env
os.environ["POSTGRES_HOST"] = "localhost"

# Load variables from the main .env file
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env")))

from netmind.db.session import get_session_factory, init_db
from netmind.models.incident import Incident, IncidentStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telemetry_worker")

async def process_telemetry():
    await init_db()
    # Force localhost:9093 for Kafka when running manually on the host
    bootstrap_servers = "localhost:9093"
    
    # Consumer for incoming telemetry
    consumer = AIOKafkaConsumer(
        "netmind.telemetry",
        bootstrap_servers=bootstrap_servers,
        group_id="telemetry-worker-group",
        auto_offset_reset="latest"
    )
    
    # Producer for outgoing incident events
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    await consumer.start()
    await producer.start()
    logger.info("📡 Telemetry worker started. Analyzing incoming network data...")
    
    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value.decode('utf-8'))
                device_id = payload.get("device_id")
                cpu = payload.get("metrics", {}).get("cpu_usage_percent", 0.0)
                
                # --- PHASE 2 BASIC ANOMALY DETECTION ---
                if cpu > 80.0:
                    logger.warning(f"🚨 ANOMALY DETECTED: {device_id} CPU at {cpu}%!")
                    
                    # Create an incident in the DB
                    correlation_id = f"high-cpu-{device_id}-{payload.get('timestamp')[:16]}"
                    
                    async with get_session_factory()() as session:
                        incident = Incident(
                            entity_id=device_id,
                            entity_type="router/switch",
                            title=f"High CPU Usage Detected on {device_id}",
                            description=f"Automated anomaly detection caught CPU spike at {cpu}%.",
                            status=IncidentStatus.DETECTED,
                            severity="CRITICAL" if cpu > 95.0 else "HIGH",
                            confidence=0.95,
                            features=payload.get("metrics"),
                            correlation_id=correlation_id
                        )
                        session.add(incident)
                        try:
                            await session.commit()
                            logger.info(f"✅ Incident saved to database: {incident.id}")
                            
                            # Publish to incident-events to trigger investigation workflow
                            await producer.send_and_wait(
                                "incident-events", 
                                {"action": "created", "incident_id": incident.id}
                            )
                        except Exception as db_err:
                            # Might fail if correlation_id already exists (idempotency)
                            await session.rollback()
                            logger.debug(f"Incident already exists for {correlation_id}")
            except Exception as e:
                logger.error(f"Error processing telemetry: {e}")
    finally:
        await consumer.stop()
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(process_telemetry())
