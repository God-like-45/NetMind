from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List
from netmind.schemas.incident import IncidentCreate, IncidentUpdate, IncidentResponse
from netmind.models.incident import Incident, IncidentStatus
from netmind.models.topology import Device, Interface, Link, Service
from netmind.db.session import get_db_session
from netmind.core.kafka import get_kafka_producer
import json

router = APIRouter(prefix="/incidents", tags=["incidents"])

async def publish_incident_event(incident_id: str, action: str):
    try:
        producer = await get_kafka_producer()
        event = {
            "incident_id": incident_id,
            "action": action,
            "system": "incident-engine"
        }
        await producer.send_and_wait("incident-events", json.dumps(event).encode("utf-8"))
    except Exception as e:
        # Ignore kafka failures for now so we don't break the API completely
        pass

@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident_in: IncidentCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        # Idempotency check using correlation_id
        if incident_in.correlation_id:
            result = await db.execute(select(Incident).where(Incident.correlation_id == incident_in.correlation_id))
            existing = result.scalars().first()
            if existing:
                return existing
                
        new_incident = Incident(
            title=incident_in.title,
            description=incident_in.description,
            severity=incident_in.severity,
            status=incident_in.status,
            entity_id=incident_in.entity_id,
            entity_type=incident_in.entity_type,
            confidence=incident_in.confidence,
            model_version=incident_in.model_version,
            features=incident_in.features,
            correlation_id=incident_in.correlation_id
        )
        db.add(new_incident)
        await db.commit()
        await db.refresh(new_incident)
        
        # Async processing trigger via background tasks (Kafka)
        background_tasks.add_task(publish_incident_event, new_incident.id, "created")
        
        return new_incident
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Incident with this correlation ID already exists")

@router.get("", response_model=List[IncidentResponse])
async def list_incidents(db: AsyncSession = Depends(get_db_session), limit: int = 100):
    result = await db.execute(select(Incident).order_by(Incident.created_at.desc()).limit(limit))
    return result.scalars().all()

@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident

@router.get("/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str, db: AsyncSession = Depends(get_db_session)):
    # Mocking timeline for the UI
    return [
        {"timestamp": "2026-09-30T10:00:00Z", "event": "DETECTED", "message": "Initial anomaly detected"},
        {"timestamp": "2026-09-30T10:01:00Z", "event": "INVESTIGATING", "message": "Worker started investigation"},
        {"timestamp": "2026-09-30T10:05:00Z", "event": "CONFIRMED", "message": "Root cause isolated to link congestion"}
    ]

@router.get("/{incident_id}/root-cause")
async def get_root_cause_baseline(incident_id: str, db: AsyncSession = Depends(get_db_session)):
    # 1. Fetch incident
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    # Baseline Root Cause Algorithm (Mocked for temporal/topology rules)
    candidates = []
    
    # Example logic: if incident is on a device, maybe a recent config change on that device
    # or an anomaly on a connected interface.
    if incident.entity_type == "device":
        candidates.append({
            "entity_id": incident.entity_id,
            "entity_type": "device",
            "reason": "Recent configuration change (BGP Policy)",
            "score": 0.85,
            "features": {"temporal_proximity": 1.0, "severity": incident.severity}
        })
        
        # Look for connected interfaces
        interfaces = (await db.execute(select(Interface).where(Interface.device_id == incident.entity_id))).scalars().all()
        for i in interfaces:
            candidates.append({
                "entity_id": i.id,
                "entity_type": "interface",
                "reason": "Neighboring node anomaly (Packet Loss Spike)",
                "score": 0.65,
                "features": {"topology_distance": 1, "severity": "HIGH"}
            })
            
    # Sort by score desc
    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "incident_id": incident_id,
        "algorithm": "heuristic_baseline",
        "candidates": candidates
    }
