import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from netmind.db.session import get_session_factory, init_db
from netmind.models.incident import Incident, IncidentStatus
import os
from dotenv import load_dotenv

# Force localhost for DB when running on host BEFORE loading imports that read env
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"

# Load variables from the main .env file
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env")))

from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from netmind.agent.workflow import build_investigation_graph
from netmind.agent.state import AgentStateEnum

async def process_incident_events():
    await init_db()
    # Force localhost:9093 for Kafka when running manually on the host
    bootstrap_servers = "localhost:9093"
    consumer = AIOKafkaConsumer(
        "incident-events",
        bootstrap_servers=bootstrap_servers,
        group_id="incident-worker-group-v2",
        auto_offset_reset="earliest"
    )
    
    await consumer.start()
    logger.info("Incident worker started. Listening for events...")
    
    # Compile graph once
    graph = build_investigation_graph()
    
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
                            entity_id = incident.entity_id
                            await session.commit()
                            logger.info(f"Incident {incident_id} moved to INVESTIGATING.")
                            
                            # Run AI Agent Graph
                            initial_state = {
                                "incident_id": incident_id,
                                "entity_id": entity_id,
                                "status": AgentStateEnum.CREATED,
                                "audit_log": [],
                                "plan": [],
                                "evidence": [],
                                "iteration_count": 0,
                                "validation_feedback": ""
                            }
                            
                            logger.info(f"Starting AI agent investigation for incident {incident_id}")
                            # Run graph (can be async, but invoke is synchronous in basic langgraph, though we can use ainvoke)
                            # Using ainvoke for asyncio compatibility
                            final_state = await graph.ainvoke(initial_state)
                            logger.info(f"Agent finished. Recommendation: {final_state.get('recommendation')}")
                            
                            # Update incident in DB
                            result = await session.execute(select(Incident).where(Incident.id == incident_id))
                            incident = result.scalars().first()
                            
                            if incident:
                                rec = final_state.get("recommendation", {})
                                finding = rec.get("finding", "Unknown")
                                action = rec.get("recommended_action", "")
                                
                                incident.description = f"AI Root Cause: {finding}\n\nRecommended Action: {action}"
                                incident.confidence = float(rec.get("confidence", 0.0))
                                
                                incident.status = IncidentStatus.CONFIRMED
                                await session.commit()
                                logger.info(f"Incident {incident_id} updated with AI analysis.")
                            
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(process_incident_events())
