import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

redis_client = None
_redis_init_tried = False

def get_redis_client():
    global redis_client, _redis_init_tried
    if redis_client is not None:
        return redis_client
    if _redis_init_tried:
        return None
    _redis_init_tried = True
    url = os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL") or ""
    if not url:
        logger.warning("REDIS_URL not set, Redis disabled")
        return None
    try:
        if "upstash" in url:
            from upstash_redis import Redis
            client = Redis.from_url(url)
            client.ping()
            redis_client = client
            logger.info("Upstash Redis connected")
            return redis_client
        import redis
        client = redis.from_url(url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3, retry_on_timeout=True, health_check_interval=30)
        client.ping()
        redis_client = client
        logger.info("Redis connected")
        return redis_client
    except Exception as e:
        logger.warning("Redis disabled: %s", e)
        redis_client = None
        return None

def rate_limit(key: str, limit: int = 5, window: int = 300) -> bool:
    client = get_redis_client()
    if not client:
        return True
    try:
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = pipe.execute()
        if ttl == -1:
            client.expire(key, window)
        return int(count) <= limit
    except Exception as e:
        logger.warning("Rate limit check failed, allowing: %s", e)
        return True

def get_cache(key: str) -> Optional[str]:
    client = get_redis_client()
    if not client:
        return None
    try:
        return client.get(key)
    except Exception as e:
        logger.warning("Redis get failed for %s: %s", key, e)
        return None

def set_cache(key: str, value: Any, ttl: int = 300) -> bool:
    client = get_redis_client()
    if not client:
        return False
    try:
        client.setex(key, ttl, str(value))
        return True
    except Exception as e:
        logger.warning("Redis set failed for %s: %s", key, e)
        return False

def delete_cache(key: str) -> bool:
    client = get_redis_client()
    if not client:
        return False
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.warning("Redis delete failed for %s: %s", key, e)
        return False

def get_redis():
    return get_redis_client()
