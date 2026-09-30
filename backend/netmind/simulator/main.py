import asyncio
import logging
from netmind.core.config import get_settings
from netmind.core.logging import configure_logging
from netmind.db.session import init_db, get_session_factory
from netmind.models.topology import Region, Device, Interface, Link, Service, DeviceType
from netmind.simulator.generator import NetworkSimulator
from netmind.core.kafka import get_kafka_producer, close_kafka_producer
from sqlalchemy import select

logger = logging.getLogger(__name__)

async def seed_topology():
    """Seed deterministic topology if none exists"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(Region).limit(1))
        if result.scalar_one_or_none():
            logger.info("Topology already exists, skipping seed")
            return
            
        logger.info("Seeding synthetic topology")
        
        # Create Regions
        r_north = Region(name="North", description="Northern Data Center")
        r_south = Region(name="South", description="Southern Edge Sites")
        session.add_all([r_north, r_south])
        await session.flush()
        
        # Create Devices
        core_1 = Device(name="core-router-01", device_type=DeviceType.ROUTER, ip_address="10.0.0.1", region_id=r_north.id)
        core_2 = Device(name="core-router-02", device_type=DeviceType.ROUTER, ip_address="10.0.0.2", region_id=r_north.id)
        edge_1 = Device(name="edge-switch-01", device_type=DeviceType.SWITCH, ip_address="10.1.0.1", region_id=r_south.id)
        edge_2 = Device(name="edge-switch-02", device_type=DeviceType.SWITCH, ip_address="10.1.0.2", region_id=r_south.id)
        session.add_all([core_1, core_2, edge_1, edge_2])
        await session.flush()
        
        # Create Interfaces
        c1_eth0 = Interface(name="eth0", device_id=core_1.id, capacity_mbps=10000.0)
        c2_eth0 = Interface(name="eth0", device_id=core_2.id, capacity_mbps=10000.0)
        e1_uplink = Interface(name="uplink", device_id=edge_1.id, capacity_mbps=1000.0)
        e2_uplink = Interface(name="uplink", device_id=edge_2.id, capacity_mbps=1000.0)
        session.add_all([c1_eth0, c2_eth0, e1_uplink, e2_uplink])
        await session.flush()
        
        # Create Links
        l1 = Link(source_interface_id=c1_eth0.id, target_interface_id=c2_eth0.id, capacity_mbps=10000.0, latency_ms=1.5)
        l2 = Link(source_interface_id=e1_uplink.id, target_interface_id=c1_eth0.id, capacity_mbps=1000.0, latency_ms=10.0)
        session.add_all([l1, l2])
        
        # Create Services
        s1 = Service(name="VoIP", service_type="voice")
        s2 = Service(name="Enterprise VPN", service_type="vpn")
        session.add_all([s1, s2])
        
        await session.commit()
        logger.info("Topology seeding complete")

async def main():
    configure_logging()
    logger.info("Starting NetMind Data Simulator")
    
    await init_db()
    await seed_topology()
    
    # Initialize Kafka
    await get_kafka_producer()
    
    simulator = NetworkSimulator()
    await simulator.load_topology()
    
    # Run simulator in background task
    sim_task = asyncio.create_task(simulator.run_loop())
    
    try:
        # Example of controlled failure injection after 15 seconds
        await asyncio.sleep(15)
        
        # Find an edge device
        edge_device = next((d for d in simulator.devices if d.name == "edge-switch-01"), None)
        if edge_device:
            logger.info("--- INJECTING FAILURE NOW ---")
            simulator.inject_failure("latency_degradation", edge_device.id, duration_sec=30)
            
        await sim_task
    except asyncio.CancelledError:
        logger.info("Simulator cancelled")
    finally:
        simulator.stop()
        await close_kafka_producer()

if __name__ == "__main__":
    asyncio.run(main())
