import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from netmind.core.kafka import publish_event
from netmind.core.config import get_kafka_settings
from netmind.schemas.events import TelemetryEvent, AlarmEvent, ConfigurationChangeEvent
from netmind.db.session import get_session_factory
from netmind.models.topology import Device, Interface, Link, Service, Region
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

class NetworkSimulator:
    def __init__(self):
        self.running = False
        self.devices = []
        self.interfaces = []
        self.active_failures = []
        self.interval = 5  # Emit every 5 seconds
    
    async def load_topology(self):
        """Load the deterministic topology from the database"""
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(Device).options(selectinload(Device.interfaces)))
            self.devices = result.scalars().all()
            logger.info(f"Loaded {len(self.devices)} devices for simulation")

    def inject_failure(self, failure_type: str, device_id: str, duration_sec: int, interface_id: str = None):
        """
        Inject a failure into the simulation.
        failure_type: 'latency_degradation', 'packet_loss_spike', 'cpu_saturation', 'device_failure', 'interface_degradation'
        """
        end_time = time.time() + duration_sec
        self.active_failures.append({
            "type": failure_type,
            "device_id": device_id,
            "interface_id": interface_id,
            "end_time": end_time,
            "start_time": time.time()
        })
        logger.info(f"Injected failure {failure_type} on {device_id} for {duration_sec}s")

    async def _emit_telemetry(self, device, interface, metric_name, value):
        event = TelemetryEvent(
            timestamp=datetime.now(timezone.utc),
            device_id=device.id,
            interface_id=interface.id if interface else None,
            metric_name=metric_name,
            metric_value=value
        )
        await publish_event(get_kafka_settings().topic_telemetry, key=device.id, value=event.model_dump(mode='json'))

    def _get_metric_value(self, base, variance, failure_impact=0.0):
        # Generate deterministic value around a base + impact
        # using a simple random walk or bounded random
        val = base + random.uniform(-variance, variance) + failure_impact
        return max(0, val) # ensure positive

    async def _generate_device_metrics(self, device):
        # Base CPU and memory
        cpu_base = 25.0
        mem_base = 40.0
        
        # Check active failures
        cpu_impact = 0.0
        is_down = False
        for f in self.active_failures:
            if f["device_id"] == device.id:
                if f["type"] == "cpu_saturation":
                    cpu_impact = 70.0 # Push to ~95%
                elif f["type"] == "device_failure":
                    is_down = True
        
        if is_down:
            return # Dead devices don't emit telemetry
            
        cpu_val = self._get_metric_value(cpu_base, 5.0, cpu_impact)
        mem_val = self._get_metric_value(mem_base, 2.0, 0.0)
        
        await self._emit_telemetry(device, None, "cpu_utilization", cpu_val)
        await self._emit_telemetry(device, None, "memory_utilization", mem_val)
        await self._emit_telemetry(device, None, "temperature", self._get_metric_value(45.0, 2.0, cpu_impact * 0.5))

    async def _generate_interface_metrics(self, device, interface):
        latency_base = 10.0
        loss_base = 0.01
        throughput_base = 500.0 # Mbps
        
        # Check active failures
        latency_impact = 0.0
        loss_impact = 0.0
        for f in self.active_failures:
            if f["device_id"] == device.id and (not f["interface_id"] or f["interface_id"] == interface.id):
                if f["type"] == "latency_degradation":
                    latency_impact = 100.0
                elif f["type"] == "packet_loss_spike":
                    loss_impact = 5.0
                elif f["type"] == "interface_degradation":
                    latency_impact = 50.0
                    loss_impact = 2.0
                    
        lat_val = self._get_metric_value(latency_base, 2.0, latency_impact)
        loss_val = self._get_metric_value(loss_base, 0.01, loss_impact)
        tp_val = self._get_metric_value(throughput_base, 50.0, -latency_impact) # throughput drops as latency goes up
        
        await self._emit_telemetry(device, interface, "latency", lat_val)
        await self._emit_telemetry(device, interface, "packet_loss", loss_val)
        await self._emit_telemetry(device, interface, "throughput", tp_val)

    async def run_loop(self):
        self.running = True
        while self.running:
            # Clean up expired failures
            now = time.time()
            self.active_failures = [f for f in self.active_failures if f["end_time"] > now]
            
            # Emit telemetry for all devices
            for device in self.devices:
                await self._generate_device_metrics(device)
                for interface in device.interfaces:
                    await self._generate_interface_metrics(device, interface)
                    
            await asyncio.sleep(self.interval)

    def stop(self):
        self.running = False

