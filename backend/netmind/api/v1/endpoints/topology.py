from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any
from netmind.db.session import get_db_session
from netmind.models.topology import Region, Device, Interface, Link, Service

router = APIRouter()

@router.get("", response_model=Dict[str, Any])
async def get_topology(db: AsyncSession = Depends(get_db_session)):
    # Fetch all topology elements
    regions = (await db.execute(select(Region))).scalars().all()
    devices = (await db.execute(select(Device))).scalars().all()
    interfaces = (await db.execute(select(Interface))).scalars().all()
    links = (await db.execute(select(Link))).scalars().all()
    services = (await db.execute(select(Service))).scalars().all()

    nodes = []
    edges = []

    for r in regions:
        nodes.append({"id": r.id, "label": r.name, "type": "region", "group": "region"})

    for d in devices:
        nodes.append({"id": d.id, "label": d.name, "type": "device", "group": d.device_type})
        edges.append({"source": d.region_id, "target": d.id, "type": "hosts"})

    for i in interfaces:
        nodes.append({"id": i.id, "label": f"{i.device_id[:5]}-{i.name}", "type": "interface", "group": "interface"})
        edges.append({"source": i.device_id, "target": i.id, "type": "hosts"})

    for l in links:
        edges.append({
            "source": l.source_interface_id, 
            "target": l.target_interface_id, 
            "type": "connected_to",
            "capacity": l.capacity_mbps,
            "latency": l.latency_ms
        })

    # Assuming Services depend on specific devices (mocking this connection as it's not strictly in schema)
    # If the schema had a relationship we would map it here. For now just list them.
    for s in services:
        nodes.append({"id": s.id, "label": s.name, "type": "service", "group": "service"})
        # We can map some mock dependencies for visual sake if needed, e.g., to the first router
        # if devices:
        #    edges.append({"source": s.id, "target": devices[0].id, "type": "depends_on"})

    return {"nodes": nodes, "links": edges}
