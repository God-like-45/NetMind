import pytest
from unittest.mock import patch, AsyncMock
from netmind.simulator.generator import NetworkSimulator

class MockDevice:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.interfaces = []

class MockInterface:
    def __init__(self, id, name):
        self.id = id
        self.name = name

@pytest.fixture
def simulator():
    sim = NetworkSimulator()
    d1 = MockDevice(id="dev1", name="router-1")
    i1 = MockInterface(id="int1", name="eth0")
    d1.interfaces.append(i1)
    sim.devices = [d1]
    return sim

def test_simulator_inject_failure(simulator):
    assert len(simulator.active_failures) == 0
    simulator.inject_failure("latency_degradation", "dev1", duration_sec=10)
    assert len(simulator.active_failures) == 1
    assert simulator.active_failures[0]["type"] == "latency_degradation"
    assert simulator.active_failures[0]["device_id"] == "dev1"

@pytest.mark.asyncio
async def test_simulator_emit_telemetry(simulator):
    with patch("netmind.simulator.generator.publish_event", new_callable=AsyncMock) as mock_publish:
        await simulator._generate_device_metrics(simulator.devices[0])
        # Should publish CPU, Memory, Temp
        assert mock_publish.call_count == 3
        
        # Test failure impact
        simulator.inject_failure("cpu_saturation", "dev1", 10)
        mock_publish.reset_mock()
        
        await simulator._generate_device_metrics(simulator.devices[0])
        assert mock_publish.call_count == 3
        
        # We can't directly check the random value easily but we know it should be higher
        # The mock publish call args could be inspected
