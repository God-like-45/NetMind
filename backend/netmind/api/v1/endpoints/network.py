from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from netmind.db.session import get_db_session
from netmind.models.topology import Device
from netmind.models.incident import Incident
from fastapi import HTTPException
import random
from datetime import datetime

router = APIRouter()

@router.get("/topology")
async def get_topology(db: AsyncSession = Depends(get_db_session)):
    """
    Get the network topology (Devices and their interfaces)
    """
    result = await db.execute(select(Device).options(selectinload(Device.interfaces), selectinload(Device.region)))
    devices = result.scalars().all()
    
    # Simple serialization for the frontend
    topology = []
    for d in devices:
        topology.append({
            "id": d.id,
            "name": d.name,
            "type": d.device_type,
            "ip_address": d.ip_address,
            "status": d.status,
            "region": d.region.name if d.region else "Unknown",
            "interfaces": [
                {
                    "id": i.id,
                    "name": i.name,
                    "capacity_mbps": i.capacity_mbps,
                    "status": i.status
                } for i in d.interfaces
            ]
        })
        
    return {"devices": topology}

@router.get("/devices")
async def get_devices(db: AsyncSession = Depends(get_db_session)):
    """
    Get all network devices
    """
    result = await db.execute(select(Device).options(selectinload(Device.region)))
    devices = result.scalars().all()
    
    device_list = []
    for d in devices:
        device_list.append({
            "id": d.id,
            "hostname": d.name,
            "type": d.device_type,
            "ip_address": d.ip_address,
            "status": d.status,
            "location": d.region.name if d.region else "Unknown",
        })
        
    return device_list

@router.get("/devices/{device_id}")
async def get_device(device_id: str, db: AsyncSession = Depends(get_db_session)):
    """
    Get detailed device information
    """
    # Find device by ID or name
    result = await db.execute(
        select(Device)
        .options(selectinload(Device.region), selectinload(Device.interfaces))
        .where((Device.id == device_id) | (Device.name == device_id))
    )
    device = result.scalars().first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    # Get recent incidents for this device
    incident_result = await db.execute(
        select(Incident)
        .where(Incident.entity_id == device.name)
        .order_by(Incident.created_at.desc())
        .limit(5)
    )
    incidents = incident_result.scalars().all()
    
    # Format incidents
    recent_incidents = [
        {
            "id": inc.id,
            "title": inc.title,
            "status": inc.status,
            "severity": inc.severity,
            "created_at": inc.created_at.isoformat()
        } for inc in incidents
    ]
    
    # Generate realistic-looking telemetry
    is_anomaly = device.status != "active"
    cpu_util = random.uniform(85, 99) if is_anomaly else random.uniform(20, 60)
    mem_util = random.uniform(80, 95) if is_anomaly else random.uniform(40, 70)
    packet_loss = random.uniform(2, 15) if is_anomaly else random.uniform(0, 0.1)
    latency = random.uniform(100, 300) if is_anomaly else random.uniform(5, 25)
    
    return {
        "identity": {
            "id": device.id,
            "hostname": device.name,
            "type": device.device_type,
            "ip_address": device.ip_address,
            "location": device.region.name if device.region else "Unknown",
            "status": device.status
        },
        "metrics": {
            "cpu_utilization": round(cpu_util, 2),
            "memory_utilization": round(mem_util, 2),
            "packet_loss": round(packet_loss, 2),
            "latency": round(latency, 2),
            "uptime": "99.99%",
            "timestamp": datetime.utcnow().isoformat()
        },
        "interfaces": [
            {
                "id": i.id,
                "name": i.name,
                "capacity_mbps": i.capacity_mbps,
                "status": i.status
            } for i in device.interfaces
        ],
        "incidents": recent_incidents,
        "recent_config_changes": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "CONFIG_UPDATE",
                "user": "system",
                "status": "SUCCESS"
            }
        ] if random.random() > 0.5 else []
    }
