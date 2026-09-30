import asyncio
import httpx
import json

async def test_query():
    query = "What should I do if a router experiences BGP flapping?"
    print(f"Query: {query}")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post("http://localhost:8001/api/v1/rag/query", json={
                "query": query,
                "user_roles": ["engineer"],
                "top_k": 3
            }, timeout=120.0)
            print(json.dumps(res.json(), indent=2))
        except Exception as e:
            print(f"Failed to query: {e}")

if __name__ == "__main__":
    asyncio.run(test_query())
