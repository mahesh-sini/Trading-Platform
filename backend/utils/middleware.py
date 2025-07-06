from fastapi import Request, Response
from fastapi.responses import JSONResponse
import time
import logging
from typing import Dict, Any
import redis
import os
import json

logger = logging.getLogger(__name__)

# Redis client for rate limiting
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

async def add_cors_headers(request: Request, call_next):
    """Add CORS headers to all responses"""
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware using Redis"""
    client_ip = request.client.host
    endpoint = request.url.path
    method = request.method
    
    # Skip rate limiting for health checks
    if endpoint in ["/health", "/ready"]:
        return await call_next(request)
    
    # Rate limit configuration
    rate_limits = {
        "POST:/v1/auth/login": {"count": 5, "window": 300},  # 5 requests per 5 minutes
        "POST:/v1/auth/register": {"count": 3, "window": 300},  # 3 requests per 5 minutes
        "GET:/v1/market": {"count": 1000, "window": 60},  # 1000 requests per minute
        "POST:/v1/trading/orders": {"count": 100, "window": 60},  # 100 orders per minute
        "GET:/v1/predictions": {"count": 50, "window": 60},  # 50 predictions per minute
        "default": {"count": 1000, "window": 60}  # Default: 1000 requests per minute
    }
    
    key = f"{method}:{endpoint}"
    limit_config = rate_limits.get(key, rate_limits["default"])
    
    # Redis key for rate limiting
    redis_key = f"rate_limit:{client_ip}:{key}"
    
    try:
        # Get current count
        current_count = redis_client.get(redis_key)
        
        if current_count is None:
            # First request
            redis_client.setex(redis_key, limit_config["window"], 1)
            current_count = 1
        else:
            current_count = int(current_count)
            
            if current_count >= limit_config["count"]:
                # Rate limit exceeded
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please try again later.",
                            "retry_after": redis_client.ttl(redis_key)
                        }
                    }
                )
            
            # Increment count
            redis_client.incr(redis_key)
            current_count += 1
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit_config["count"])
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit_config["count"] - current_count))
        response.headers["X-RateLimit-Reset"] = str(time.time() + redis_client.ttl(redis_key))
        
        return response
        
    except Exception as e:
        logger.warning(f"Rate limiting error: {str(e)}")
        # If Redis is down, proceed without rate limiting
        return await call_next(request)

async def request_logging_middleware(request: Request, call_next):
    """Log all requests with timing and response status"""
    start_time = time.time()
    
    # Extract request info
    method = request.method
    url = str(request.url)
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log request
    logger.info(
        "Request processed",
        method=method,
        url=url,
        status_code=response.status_code,
        process_time=f"{process_time:.3f}s",
        client_ip=client_ip,
        user_agent=user_agent
    )
    
    # Add process time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

async def error_handling_middleware(request: Request, call_next):
    """Global error handling middleware"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(
            "Unhandled error",
            error=str(e),
            method=request.method,
            url=str(request.url),
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "timestamp": time.time()
                }
            }
        )

def create_request_id_middleware():
    """Create unique request ID for tracing"""
    async def middleware(request: Request, call_next):
        import uuid
        request_id = str(uuid.uuid4())
        
        # Add to request state
        request.state.request_id = request_id
        
        response = await call_next(request)
        
        # Add to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    return middleware