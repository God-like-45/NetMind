import asyncio
import os
from dotenv import load_dotenv

# Force localhost for DB since we are running on host
os.environ["POSTGRES_HOST"] = "localhost"

# Load variables from the main .env file
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env")))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from netmind.db.session import get_session_factory, init_db
from netmind.models.topology import Region, Device, DeviceType, Interface, Link, Service

async def seed():
    print("Initializing Database...")
    await init_db()
    
    async with get_session_factory()() as session:
        print("Creating Regions...")
        nyc = Region(id="nyc-reg-01", name="NYC", description="New York Data Center")
        ldn = Region(id="ldn-reg-01", name="LDN", description="London Data Center")
        
        # Upsert regions
        for reg in [nyc, ldn]:
            existing = (await session.execute(select(Region).where(Region.id == reg.id))).scalars().first()
            if not existing:
                session.add(reg)
        
        print("Creating Devices...")
        devices = [
            Device(id="router-core-01", name="NYC Core Router", device_type=DeviceType.ROUTER, ip_address="10.0.1.254", region_id="nyc-reg-01"),
            Device(id="switch-access-01", name="NYC Access Switch", device_type=DeviceType.SWITCH, ip_address="10.0.1.10", region_id="nyc-reg-01"),
            Device(id="router-core-02", name="LDN Core Router", device_type=DeviceType.ROUTER, ip_address="10.0.2.254", region_id="ldn-reg-01"),
            Device(id="fw-edge-01", name="LDN Edge Firewall", device_type=DeviceType.FIREWALL, ip_address="10.0.2.1", region_id="ldn-reg-01"),
        ]
        
        for dev in devices:
            existing = (await session.execute(select(Device).where(Device.id == dev.id))).scalars().first()
            if not existing:
                session.add(dev)
                
        print("Creating Interfaces & Links...")
        # Create interfaces for router-core-01
        i1 = Interface(id="if-rc01-0/0", name="Eth0/0", device_id="router-core-01", capacity_mbps=10000.0)
        i2 = Interface(id="if-rc01-0/1", name="Eth0/1", device_id="router-core-01", capacity_mbps=1000.0)
        # Create interfaces for switch-access-01
        i3 = Interface(id="if-sa01-1/1", name="Gi1/1", device_id="switch-access-01", capacity_mbps=1000.0)
        # Create interfaces for router-core-02
        i4 = Interface(id="if-rc02-0/0", name="Eth0/0", device_id="router-core-02", capacity_mbps=10000.0)
        i5 = Interface(id="if-rc02-0/1", name="Eth0/1", device_id="router-core-02", capacity_mbps=1000.0)
        # Create interface for fw-edge-01
        i6 = Interface(id="if-fw01-eth1", name="Eth1", device_id="fw-edge-01", capacity_mbps=1000.0)
        
        interfaces = [i1, i2, i3, i4, i5, i6]
        for iface in interfaces:
            existing = (await session.execute(select(Interface).where(Interface.id == iface.id))).scalars().first()
            if not existing:
                session.add(iface)
                
        # Flush to DB to resolve foreign key constraints before adding links
        await session.flush()
                
        # Link NYC Core to NYC Access
        link1 = Link(id="link-nyc-core-acc", source_interface_id=i2.id, target_interface_id=i3.id, capacity_mbps=1000.0, latency_ms=1.2)
        # Link NYC Core to LDN Core (WAN)
        link2 = Link(id="link-wan-nyc-ldn", source_interface_id=i1.id, target_interface_id=i4.id, capacity_mbps=10000.0, latency_ms=85.5)
        # Link LDN Core to LDN Firewall
        link3 = Link(id="link-ldn-core-fw", source_interface_id=i5.id, target_interface_id=i6.id, capacity_mbps=1000.0, latency_ms=0.5)
        
        for link in [link1, link2, link3]:
            existing = (await session.execute(select(Link).where(Link.id == link.id))).scalars().first()
            if not existing:
                session.add(link)
                
        print("Committing to database...")
        try:
            await session.commit()
            print("✅ Topology successfully seeded!")
        except Exception as e:
            await session.rollback()
            print("Failed to seed topology. It might already exist.")
            print(e)

if __name__ == "__main__":
    asyncio.run(seed())
