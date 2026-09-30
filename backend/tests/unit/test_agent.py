import pytest
from netmind.agent.tools import get_device_telemetry

def test_tool_input_validation():
    # Test valid device tool with permissions
    result = get_device_telemetry("core-rtr-01", ["engineer"])
    assert "latency" in result
    
    # Test invalid tool permissions
    with pytest.raises(PermissionError):
        get_device_telemetry("core-rtr-01", ["viewer"])
        
def test_agent_state_transitions():
    # Placeholder for checking that agent properly halts at waiting for human approval
    # Without real dependencies, we just test the logic constants
    from netmind.agent.state import AgentStateEnum
    assert AgentStateEnum.WAITING_FOR_APPROVAL == "WAITING_FOR_APPROVAL"
