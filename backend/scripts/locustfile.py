from locust import HttpUser, task, between
import random

class NetMindLoadTestUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def view_dashboard(self):
        """Simulate users refreshing the overview dashboard."""
        self.client.get("/api/v1/network/topology", headers={"Authorization": "Bearer fake_token"})
        
    @task(1)
    def view_incidents(self):
        """Simulate users checking active incidents."""
        self.client.get("/api/v1/incidents", headers={"Authorization": "Bearer fake_token"})

    @task(1)
    def trigger_investigation(self):
        """Simulate heavy agentic load."""
        # For safety in load testing, hit a read-only or stubbed endpoint if possible
        # or the actual investigation API if specifically benchmarking LLM throughput
        self.client.post(
            "/api/v1/agent/investigate", 
            json={"incident_id": f"INC-LOAD-{random.randint(100, 999)}"},
            headers={"Authorization": "Bearer fake_token"}
        )

# NOTE: These tests measure the ACTUAL local environment capacity. 
# Do NOT claim production capacity based on these results.
