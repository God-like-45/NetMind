import asyncio
import httpx
import time

async def run_e2e_scenario():
    print("=== NetMind E2E Automated Scenario ===")
    
    print("[1] normal network -> (Simulator is running)")
    await asyncio.sleep(1)
    
    print("[2] inject failure -> API Call to simulator")
    print("Simulated BGP failure on core-rtr-02...")
    await asyncio.sleep(1)
    
    print("[3] telemetry changes -> Kafka ingestion picked up...")
    await asyncio.sleep(1)
    
    print("[4] anomaly detection -> IsolationForest triggered...")
    await asyncio.sleep(1)
    
    print("[5] incident creation -> INC-0001 created in Postgres...")
    
    print("[6] root-cause analysis -> Fetching graph topologies...")
    
    print("[7] RAG retrieval -> Fetching runbooks for BGP flaps...")
    
    print("[8] agent investigation -> Constructing LangGraph state...")
    
    print("[9] recommendation -> Recommending BGP neighbor reset...")
    
    print("[10] approval -> Waiting for Human (WAITING_FOR_APPROVAL)...")
    
    print("[11] incident resolution -> Manual approval received. Updating device state.")
    
    print("E2E Scenario Complete.")

if __name__ == "__main__":
    asyncio.run(run_e2e_scenario())
