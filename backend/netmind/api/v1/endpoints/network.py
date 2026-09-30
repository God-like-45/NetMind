from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from netmind.db.session import get_db_session
from netmind.models.topology import Device

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
