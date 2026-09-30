import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from netmind.schemas.events import TelemetryEvent, AlarmEvent

def test_telemetry_event_valid():
    event = TelemetryEvent(
        timestamp=datetime.now(timezone.utc),
        device_id="dev1",
        metric_name="latency",
        metric_value=12.5
    )
    assert event.device_id == "dev1"
    assert event.metric_value == 12.5

def test_telemetry_event_missing_fields():
    with pytest.raises(ValidationError):
        TelemetryEvent(device_id="dev1", metric_name="latency")

def test_alarm_event_valid_severity():
    event = AlarmEvent(
        timestamp=datetime.now(timezone.utc),
        alarm_id="al1",
        device_id="dev1",
        severity="CRITICAL",
        description="High latency"
    )
    assert event.severity == "CRITICAL"

def test_alarm_event_invalid_severity():
    with pytest.raises(ValidationError):
        AlarmEvent(
            timestamp=datetime.now(timezone.utc),
            alarm_id="al1",
            device_id="dev1",
            severity="BROKEN", # Invalid Literal
            description="Bad severity"
        )
