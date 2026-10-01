import os
import time
import uuid
import logging
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("netmind.access")

class ProductionEngineeringMiddleware(BaseHTTPMiddleware):
    """
    Implements Phase 6 Production Engineering Hardening Requirements:
    - Structured Logging
    - Request IDs & Correlation IDs
    - Latency Metrics
    - Error Metrics Tracking
    - Redis-based Rate Limiting (stubbed for illustration as actual Redis connection can fail if down)
    """
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis = redis_client

    async def check_rate_limit(self, client_ip: str) -> bool:
        """
        Uses Redis for rate limiting (Token Bucket or Fixed Window).
        Redis is explicitly used here for rate limiting to prevent API abuse,
        and for temporary state coordination across multiple backend nodes.
        """
        if not self.redis:
            return True # Pass-through if redis isn't configured
            
        try:
            # Simple fixed window rate limiting: 100 requests per minute
            key = f"rate_limit:{client_ip}:{int(time.time() / 60)}"
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, 60)
            return count <= 100
        except Exception:
            # Fail open if Redis is down, but log error
            logger.error("Redis rate limit check failed")
            return True

    async def dispatch(self, request: Request, call_next):
        # 1. Request / Correlation IDs
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        correlation_id = request.headers.get("X-Correlation-ID", request_id)
        
        # 2. Rate Limiting Check
        client_ip = request.client.host if request.client else "127.0.0.1"
        allowed = await self.check_rate_limit(client_ip)
        if not allowed:
            return JSONResponse(
                status_code=429, 
                content={"error": "Too Many Requests", "message": "Rate limit exceeded"}
            )
            
        # 3. Request Processing & Latency tracking
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Inject headers back
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            latency_ms = (time.time() - start_time) * 1000
            
            # 4. Structured Logging (Observability)
            log_data = {
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": round(latency_ms, 2),
                "client_ip": client_ip,
                "type": "access_log"
            }
            if status_code >= 400:
                logger.error(json.dumps(log_data))
            else:
                logger.info(json.dumps(log_data))
                
        return response
