import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from netmind.db.session import get_session_factory, init_db
from netmind.models.incident import Incident, IncidentStatus
import os
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_incident_events():
    await init_db()
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093")
    consumer = AIOKafkaConsumer(
        "incident-events",
        bootstrap_servers=bootstrap_servers,
        group_id="incident-worker-group",
        auto_offset_reset="earliest"
    )
    
    await consumer.start()
    logger.info("Incident worker started. Listening for events...")
    
    try:
        async for msg in consumer:
            try:
                event = json.loads(msg.value.decode('utf-8'))
                logger.info(f"Received event: {event}")
                incident_id = event.get("incident_id")
                
                if event.get("action") == "created" and incident_id:
                    # Async mock investigation step
                    async with get_session_factory()() as session:
                        result = await session.execute(select(Incident).where(Incident.id == incident_id))
                        incident = result.scalars().first()
                        if incident and incident.status == IncidentStatus.DETECTED:
                            incident.status = IncidentStatus.INVESTIGATING
                            await session.commit()
                            logger.info(f"Incident {incident_id} moved to INVESTIGATING.")
                            
                    # Simulate processing delay
                    await asyncio.sleep(2)
                    
                    async with get_session_factory()() as session:
                        result = await session.execute(select(Incident).where(Incident.id == incident_id))
                        incident = result.scalars().first()
                        if incident and incident.status == IncidentStatus.INVESTIGATING:
                            # Decide on confirmation based on confidence (mock logic)
                            if incident.confidence and incident.confidence > 0.8:
                                incident.status = IncidentStatus.CONFIRMED
                            else:
                                incident.status = IncidentStatus.RESOLVED # False alarm
                            await session.commit()
                            logger.info(f"Incident {incident_id} moved to {incident.status.value}.")
                            
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(process_incident_events())
