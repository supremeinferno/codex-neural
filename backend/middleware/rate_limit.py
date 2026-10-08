from __future__ import annotations

import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

try:
    import redis
except Exception:
    redis = None

from backend.auth import record_event

RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
RATE_LIMIT_EXCLUDED_PATHS = {"/api", "/api/health", "/api/session"}
RATE_LIMIT_ALGORITHM = os.getenv("RATE_LIMIT_ALGORITHM", "sliding_window").strip().lower()
RATE_LIMIT_USE_REDIS = os.getenv("RATE_LIMIT_USE_REDIS", "true").strip().lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REQUEST_BUCKETS = {}
RATE_LIMIT_CLIENT = None


def get_rate_limit_client():
    global RATE_LIMIT_CLIENT

    if not RATE_LIMIT_USE_REDIS or redis is None:
        return None

    if RATE_LIMIT_CLIENT is not None:
        return RATE_LIMIT_CLIENT

    try:
        RATE_LIMIT_CLIENT = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        RATE_LIMIT_CLIENT.ping()
        return RATE_LIMIT_CLIENT
    except Exception:
        RATE_LIMIT_CLIENT = None
        return None


def _memory_rate_limit(bucket_key, now):
    if RATE_LIMIT_ALGORITHM == "fixed_window":
        bucket = REQUEST_BUCKETS.setdefault(
            bucket_key,
            {"window_start": now, "count": 0},
        )
        if now - bucket["window_start"] >= RATE_LIMIT_WINDOW_SECONDS:
            bucket["window_start"] = now
            bucket["count"] = 0
        if bucket["count"] >= RATE_LIMIT_MAX_REQUESTS:
            return False
        bucket["count"] += 1
        return True

    if RATE_LIMIT_ALGORITHM == "token_bucket":
        bucket = REQUEST_BUCKETS.setdefault(
            bucket_key,
            {"tokens": float(RATE_LIMIT_MAX_REQUESTS), "last_refill": now},
        )
        elapsed = max(0.0, now - bucket["last_refill"])
        refill_rate = RATE_LIMIT_MAX_REQUESTS / RATE_LIMIT_WINDOW_SECONDS
        bucket["tokens"] = min(
            float(RATE_LIMIT_MAX_REQUESTS),
            bucket["tokens"] + (elapsed * refill_rate),
        )
        bucket["last_refill"] = now
        if bucket["tokens"] < 1:
            return False
        bucket["tokens"] -= 1
        return True

    bucket = REQUEST_BUCKETS.setdefault(bucket_key, [])
    bucket[:] = [
        timestamp
        for timestamp in bucket
        if now - timestamp < RATE_LIMIT_WINDOW_SECONDS
    ]
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    bucket.append(now)
    return True


def _redis_rate_limit(bucket_key, now):
    client = get_rate_limit_client()
    if client is None:
        return _memory_rate_limit(bucket_key, now)

    if RATE_LIMIT_ALGORITHM == "fixed_window":
        script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local existing = tonumber(redis.call('GET', key))
        if existing == nil then
            redis.call('SET', key, 1, 'EX', window)
            return 1
        end
        if existing >= limit then
            return 0
        end
        redis.call('INCR', key)
        return 1
        """
        return client.eval(
            script,
            1,
            bucket_key,
            RATE_LIMIT_MAX_REQUESTS,
            RATE_LIMIT_WINDOW_SECONDS,
        ) == 1

    if RATE_LIMIT_ALGORITHM == "token_bucket":
        script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local tokens = tonumber(redis.call('HGET', key, 'tokens'))
        if tokens == nil then tokens = limit end
        local last = tonumber(redis.call('HGET', key, 'last'))
        if last == nil then last = now end
        local elapsed = math.max(0, now - last)
        local refill_rate = limit / window
        tokens = math.min(limit, tokens + (elapsed * refill_rate))
        if tokens < 1 then
            redis.call('HSET', key, 'tokens', tokens, 'last', now)
            redis.call('EXPIRE', key, math.ceil(window) + 1)
            return 0
        end
        tokens = tokens - 1
        redis.call('HSET', key, 'tokens', tokens, 'last', now)
        redis.call('EXPIRE', key, math.ceil(window) + 1)
        return 1
        """
        return client.eval(
            script,
            1,
            bucket_key,
            RATE_LIMIT_MAX_REQUESTS,
            RATE_LIMIT_WINDOW_SECONDS,
            now,
        ) == 1

    script = """
    local key = KEYS[1]
    local window = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local marker = tostring(now) .. ':' .. tostring(ARGV[4])
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
    local count = tonumber(redis.call('ZCARD', key)) or 0
    if count >= limit then
        return 0
    end
    redis.call('ZADD', key, now, marker)
    redis.call('EXPIRE', key, window + 1)
    return 1
    """
    return client.eval(
        script,
        1,
        bucket_key,
        RATE_LIMIT_WINDOW_SECONDS,
        RATE_LIMIT_MAX_REQUESTS,
        now,
        time.time_ns(),
    ) == 1


def rate_limit_request(client_ip, path):
    bucket_key = f"rate_limit:{RATE_LIMIT_ALGORITHM}:{client_ip}:{path}"
    return _redis_rate_limit(bucket_key, time.time())


def install_rate_limit_middleware(app: FastAPI):
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        path = request.url.path
        if path in RATE_LIMIT_EXCLUDED_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not rate_limit_request(client_ip, path):
            record_event(
                event_type="rate_limit_hit",
                path=path,
                details={
                    "ip_address": client_ip,
                    "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
                    "max_requests": RATE_LIMIT_MAX_REQUESTS,
                    "algorithm": RATE_LIMIT_ALGORITHM,
                    "backend": "redis" if get_rate_limit_client() is not None else "memory",
                },
                ip_address=client_ip,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Too many requests. Please try again later.",
                },
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )
        return await call_next(request)
