import os
import redis

redis_client = None

try:
    url = os.getenv("REDIS_URL")
    if url:
        redis_client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        redis_client.ping()
        print("✅ Redis connected:", url[:30])
    else:
        print("⚠️ REDIS_URL not set - running without Redis")
except Exception as e:
    print(f"⚠️ Redis disabled: {e}")
    redis_client = None

def rate_limit(key: str, limit=5, window=300):
    """Simple rate limit, works even if redis is None"""
    if not redis_client:
        return True
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, window)
        return count <= limit
    except:
        return True
