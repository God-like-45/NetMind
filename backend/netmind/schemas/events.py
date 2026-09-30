from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class TelemetryEvent(BaseModel):
    timestamp: datetime
    device_id: str
    interface_id: str | None = None
    metric_name: str
    metric_value: float

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AlarmEvent(BaseModel):
    timestamp: datetime
    alarm_id: str
    device_id: str
    severity: Literal["CRITICAL", "MAJOR", "MINOR", "WARNING", "CLEARED"]
    description: str


class ConfigurationChangeEvent(BaseModel):
    timestamp: datetime
    device_id: str
    changed_by: str
    change_type: Literal["UPDATE", "ROLLBACK", "COMMIT"]
    description: str


class IncidentEvent(BaseModel):
    timestamp: datetime
    incident_id: str
    status: Literal["OPEN", "INVESTIGATING", "RESOLVED"]
    description: str
    related_alarms: list[str] = Field(default_factory=list)
