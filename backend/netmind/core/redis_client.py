import os
import redis.asyncio as redis
from netmind.core.config import get_settings

_redis_pool = None

async def init_redis():
    global _redis_pool
    if not _redis_pool:
        settings = get_settings()
        
        # We explicitly use Redis for:
        # 1. Rate Limiting (Token Bucket / Fixed Window) - prevents API abuse
        # 2. Temporary State / Idempotency keys (e.g. tracking processed Kafka messages)
        # 3. Caching of frequently accessed static data (e.g. topology details)
        
        _redis_pool = redis.ConnectionPool(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True
        )

def get_redis_client() -> redis.Redis:
    if not _redis_pool:
        raise RuntimeError("Redis pool not initialized. Call init_redis() at startup.")
    return redis.Redis(connection_pool=_redis_pool)

async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
