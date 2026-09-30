import asyncio
import httpx

DOCS = [
    {
        "text": """BGP Policy Runbook
When a router experiences BGP flapping or high CPU due to BGP route calculations, it is often related to a recent policy change.
To mitigate:
1. Identify the recent commit on the router.
2. Rollback the configuration.
3. Clear BGP sessions gracefully using `clear ip bgp * soft`.
""",
        "metadata": {"source": "runbook_bgp.md", "type": "runbook"},
        "allowed_roles": ["engineer", "admin"]
    },
    {
        "text": """Link Congestion Troubleshooting Guide
Link down anomalies or high packet loss on interfaces connected to the core network usually indicate physical layer issues or microbursts.
Steps to isolate:
1. Check interface optical levels (DOM).
2. Verify QoS queue drops.
3. If QoS drops are high, consider traffic engineering (TE) to reroute traffic.
""",
        "metadata": {"source": "guide_link_congestion.md", "type": "troubleshooting"},
        "allowed_roles": ["engineer", "admin", "viewer"]
    },
    {
        "text": """Historical Incident Report: INC-2025-04
A massive outage occurred in the South region.
Root cause: An unapproved firewall rule blocked OSPF packets, causing OSPF neighbor adjacency to drop across 4 edge switches.
Resolution: Reverted the firewall rule and updated the CI/CD pipeline to lint firewall rules against control plane protocols.
""",
        "metadata": {"source": "INC-2025-04_postmortem.md", "type": "postmortem"},
        "allowed_roles": ["admin"]
    }
]

async def seed_docs():
    async with httpx.AsyncClient() as client:
        for doc in DOCS:
            try:
                res = await client.post("http://localhost:8001/api/v1/rag/ingest", json={
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "allowed_roles": doc["allowed_roles"]
                }, timeout=30.0)
                print(f"Ingested {doc['metadata']['source']}: {res.json()}")
            except Exception as e:
                print(f"Failed to ingest {doc['metadata']['source']}: {e}")

if __name__ == "__main__":
    asyncio.run(seed_docs())
