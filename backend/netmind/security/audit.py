import time
import json
import logging
from typing import Any, Dict

# In a production environment, this would write to a specialized append-only datastore
# such as an isolated Kafka topic or a WORM (Write Once Read Many) storage system.
audit_logger = logging.getLogger("netmind_audit")
audit_logger.setLevel(logging.INFO)
# Avoid standard formatting to ensure pure JSON
handler = logging.StreamHandler()
audit_logger.addHandler(handler)
# Remove default handlers
audit_logger.propagate = False

class AuditAction:
    LOGIN = "LOGIN"
    INCIDENT_ACCESS = "INCIDENT_ACCESS"
    INVESTIGATION_START = "INVESTIGATION_START"
    DOCUMENT_RETRIEVAL = "DOCUMENT_RETRIEVAL"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    RECOMMENDATION_APPROVAL = "RECOMMENDATION_APPROVAL"
    CONFIG_CHANGE = "CONFIG_CHANGE"

class AuditLog:
    @staticmethod
    def record(user: str, action: str, resource: str, details: Dict[str, Any], status: str = "SUCCESS"):
        """
        Record an immutable audit log entry.
        """
        record = {
            "timestamp": time.time(),
            "user": user,
            "action": action,
            "resource": resource,
            "status": status,
            "details": details
        }
        # In a real scenario, sign the record cryptographically to guarantee immutability
        audit_logger.info(json.dumps(record))
