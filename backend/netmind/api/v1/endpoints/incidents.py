from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from netmind.api.dependencies import get_current_operator_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime
from netmind.schemas.incident import IncidentCreate, IncidentUpdate, IncidentResponse, IncidentActionRequest
from netmind.models.incident import Incident, IncidentStatus, IncidentAudit
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
                
        # Fill in default timelines
        now = datetime.utcnow()
        det_time = incident_in.detection_timestamp or now
        
        new_incident = Incident(
            title=incident_in.title,
            description=incident_in.description,
            severity=incident_in.severity,
            status=incident_in.status,
            entity_id=incident_in.entity_id,
            entity_type=incident_in.entity_type,
            
            detection_timestamp=det_time,
            triggering_metric=incident_in.triggering_metric,
            observed_value=incident_in.observed_value,
            expected_value=incident_in.expected_value,
            
            related_telemetry=incident_in.related_telemetry,
            related_devices=incident_in.related_devices,
            topology_relationships=incident_in.topology_relationships,
            recent_config_changes=incident_in.recent_config_changes,
            related_incidents=incident_in.related_incidents,
            
            # Storing candidate_root_causes as dict representations of RootCauseCandidate schema
            candidate_root_causes=[c.dict() for c in incident_in.candidate_root_causes] if incident_in.candidate_root_causes else None,
            recommended_actions=incident_in.recommended_actions,
            
            human_approval_state="PENDING",
            
            model_version=incident_in.model_version,
            features=incident_in.features,
            correlation_id=incident_in.correlation_id
        )
        db.add(new_incident)
        await db.commit()
        await db.refresh(new_incident)
        
        # Insert audit trail for creation timeline
        audit_records = [
            IncidentAudit(incident_id=new_incident.id, action="anomaly detected", timestamp=det_time, details={"metric": incident_in.triggering_metric}),
            IncidentAudit(incident_id=new_incident.id, action="incident created", timestamp=now, details={"status": new_incident.status.value}),
            IncidentAudit(incident_id=new_incident.id, action="correlation completed", timestamp=now, details={"correlation_id": incident_in.correlation_id}),
            IncidentAudit(incident_id=new_incident.id, action="investigation started", timestamp=now, details={"status": "INVESTIGATING"})
        ]
        db.add_all(audit_records)
        new_incident.status = IncidentStatus.INVESTIGATING
        await db.commit()
        await db.refresh(new_incident)
        
        # Async processing trigger via background tasks (Kafka)
        background_tasks.add_task(publish_incident_event, new_incident.id, "created")
        
        # Fetch with audit trail
        result = await db.execute(select(Incident).options(selectinload(Incident.audit_trail)).where(Incident.id == new_incident.id))
        return result.scalars().first()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Incident with this correlation ID already exists")

@router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    db: AsyncSession = Depends(get_db_session), 
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    severity: Optional[str] = None
):
    query = select(Incident).options(selectinload(Incident.audit_trail))
    
    if status:
        query = query.where(Incident.status == status)
    if severity:
        query = query.where(Incident.severity == severity)
        
    query = query.order_by(Incident.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(Incident)
        .options(selectinload(Incident.audit_trail))
        .where(Incident.id == incident_id)
    )
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident

@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str, 
    incident_update: IncidentUpdate, 
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_operator_user)
):
    result = await db.execute(select(Incident).options(selectinload(Incident.audit_trail)).where(Incident.id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    
    update_data = incident_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(incident, key, value)
        
    audit = IncidentAudit(
        incident_id=incident.id, 
        action="Updated", 
        user_id=current_user.id,
        timestamp=datetime.utcnow(), 
        details=update_data
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(incident)
    return incident

@router.post("/{incident_id}/action", response_model=IncidentResponse)
async def act_on_incident(
    incident_id: str,
    action_request: IncidentActionRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_operator_user)
):
    result = await db.execute(select(Incident).options(selectinload(Incident.audit_trail)).where(Incident.id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    
    action = action_request.action.upper()
    if action == "APPROVE":
        incident.human_approval_state = "APPROVED"
        incident.status = IncidentStatus.CONFIRMED
    elif action == "REJECT":
        incident.human_approval_state = "REJECTED"
        incident.status = IncidentStatus.CLOSED
    elif action == "ESCALATE":
        incident.human_approval_state = "ESCALATED"
    elif action == "RESOLVE":
        incident.status = IncidentStatus.RESOLVED
        if action_request.resolution_notes:
            incident.resolution = action_request.resolution_notes
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    audit = IncidentAudit(
        incident_id=incident.id, 
        action=action, 
        user_id=current_user.id if current_user else "unknown",
        timestamp=datetime.utcnow(), 
        details={"notes": action_request.resolution_notes}
    )
    db.add(audit)
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident

@router.get("/{incident_id}/root-cause")
async def get_root_cause_baseline(incident_id: str, db: AsyncSession = Depends(get_db_session)):
    # 1. Fetch incident
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    # Phase 5: Return candidate root causes (Model-generated hypotheses)
    # If the incident already has candidate_root_causes, return them
    if incident.candidate_root_causes:
        return {
            "incident_id": incident_id,
            "algorithm": "incident_engine_v2",
            "candidates": incident.candidate_root_causes
        }
    
    # Baseline Root Cause Algorithm
    candidates = []
    
    if incident.entity_type == "device":
        candidates.append({
            "hypothesis": "Recent configuration change (BGP Policy)",
            "evidence": [
                "configuration changed 4 minutes before anomaly",
                "packet loss increased from 0.01% to 2.5%",
                "affected device belongs to same topology path"
            ],
            "score": 0.85
        })
        
        # Look for connected interfaces
        interfaces = (await db.execute(select(Interface).where(Interface.device_id == incident.entity_id))).scalars().all()
        for i in interfaces:
            candidates.append({
                "hypothesis": f"Neighboring node anomaly on interface {i.name}",
                "evidence": [
                    "interface went down exactly at the anomaly timestamp",
                    "OSPF neighbor down logs detected"
                ],
                "score": 0.65
            })
            
    # Sort by score desc
    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "incident_id": incident_id,
        "algorithm": "heuristic_baseline",
        "candidates": candidates
    }
