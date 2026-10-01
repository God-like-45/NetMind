import os
import sys
from dotenv import load_dotenv

# QDRANT_HOST will be taken from env vars

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), ".env")))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from netmind.rag.ingest import KnowledgeIngestor

RUNBOOKS = [
    {
        "text": """# Router Core 02 - CPU Spikes
        When Router Core 02 experiences high CPU utilization (over 85%), it is typically caused by a routing loop in the BGP tables or an excessive number of active connections dropping into software switching instead of hardware forwarding.
        
        Recommended Action: 
        1. Check active BGP sessions. 
        2. If active connections exceed 4000, enable hardware offloading or rate-limit control plane traffic.
        3. Do NOT restart the router during peak hours, as it will cause a catastrophic failover to Router Core 01.""",
        "metadata": {"source": "runbook_router_cpu.md", "type": "troubleshooting"},
        "allowed_roles": ["engineer", "admin"]
    },
    {
        "text": """# Access Switch 01 - Port Flapping
        If Gi1/1 on Switch Access 01 flaps more than 3 times in 5 minutes, it usually indicates a faulty transceiver or bad fiber patch cable.
        
        Recommended Action:
        1. Shut down the interface temporarily to prevent STP recalculations.
        2. Dispatch a technician to replace the SFP module.
        3. Bring the interface back online and monitor for CRC errors.""",
        "metadata": {"source": "runbook_switch_port.md", "type": "troubleshooting"},
        "allowed_roles": ["engineer", "admin"]
    },
    {
        "text": """# Edge Firewall - High CPU
        High CPU on edge firewalls is often indicative of a volumetric DDoS attack. If CPU spikes above 80%, check the session tables immediately.
        
        Recommended Action:
        1. Review top talkers in the session table.
        2. Enable SYN flood protection if TCP connections are abnormally high.
        3. If traffic originates from a specific geolocation, apply temporary geo-blocking rules.""",
        "metadata": {"source": "runbook_firewall_cpu.md", "type": "security"},
        "allowed_roles": ["security", "admin", "engineer"]
    }
]

def seed_knowledge():
    print("Initializing Knowledge Ingestor...")
    ingestor = KnowledgeIngestor()
    
    total_chunks = 0
    for rb in RUNBOOKS:
        print(f"Ingesting: {rb['metadata']['source']}")
        chunks = ingestor.ingest_document(
            text=rb["text"],
            metadata=rb["metadata"],
            allowed_roles=rb["allowed_roles"]
        )
        total_chunks += chunks
        
    print(f"Success! Ingested {len(RUNBOOKS)} documents into {total_chunks} chunks.")

if __name__ == "__main__":
    seed_knowledge()
