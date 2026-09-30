import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "http://localhost:8000/api/v1"

async def test_duplicate_events():
    logger.info("Testing Duplicate Events & Idempotency...")
    payload = {
        "title": "High CPU Anomaly on Router B",
        "severity": "HIGH",
        "entity_id": "router-b-id",
        "entity_type": "device",
        "correlation_id": "corr-cpu-router-b-2026",
        "confidence": 0.95,
        "model_version": "isolation_forest-v2"
    }
    
    async with httpx.AsyncClient() as client:
        # Request 1
        res1 = await client.post(f"{API_URL}/incidents", json=payload)
        logger.info(f"Req 1 Status: {res1.status_code}")
        
        # Request 2 (Duplicate)
        res2 = await client.post(f"{API_URL}/incidents", json=payload)
        logger.info(f"Req 2 Status: {res2.status_code} (Should be 200 or 409 but effectively blocked duplicate)")
        
        if res1.status_code == 201 and (res2.status_code == 409 or res1.json()['id'] == res2.json()['id']):
            logger.info("Duplicate events test passed.")
        else:
            logger.error("Duplicate events test failed.")

async def test_concurrent_creation():
    logger.info("Testing Concurrent Incident Creation...")
    payload = {
        "title": "Link Down Anomaly",
        "severity": "CRITICAL",
        "entity_id": "link-123",
        "entity_type": "link",
        "correlation_id": "corr-link-down-123",
        "confidence": 0.99
    }
    
    async with httpx.AsyncClient() as client:
        tasks = [client.post(f"{API_URL}/incidents", json=payload) for _ in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code in (201, 200))
        conflict_count = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 409)
        
        logger.info(f"Successful: {success_count}, Conflicts: {conflict_count}")
        if success_count + conflict_count == 5:
            logger.info("Concurrent test handled successfully.")
            
async def test_inference_endpoints():
    logger.info("Testing Inference Endpoints...")
    async with httpx.AsyncClient() as client:
        res1 = await client.post(f"{API_URL}/predictions/anomaly", json={
            "entity_id": "device-1",
            "entity_type": "device",
            "features": {"rolling_mean_latency": 160.0}
        })
        logger.info(f"Anomaly Response: {res1.json()}")
        
        res2 = await client.post(f"{API_URL}/predictions/failure-risk", json={
            "entity_id": "device-1",
            "entity_type": "device",
            "features": {"rolling_z_score_cpu": 5.0}
        })
        logger.info(f"Failure Risk Response: {res2.json()}")

async def main():
    await test_inference_endpoints()
    await test_duplicate_events()
    await test_concurrent_creation()
    logger.info("All tests executed.")

if __name__ == "__main__":
    asyncio.run(main())
