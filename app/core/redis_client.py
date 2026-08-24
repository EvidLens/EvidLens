import os
from dotenv import load_dotenv

load_dotenv()

redis_client = None

try:
    url = os.getenv("REDIS_URL")
    if not url:
        print("⚠️ REDIS_URL not set")
    elif "upstash" in url:
        # For Upstash URL like rediss://default:xxx@us1-xxx.upstash.io:6379
        from upstash_redis import Redis
        redis_client = Redis.from_env() if not url else Redis.from_url(url)
        redis_client.ping()
        print(f"✅ Upstash Redis connected: {url[:45]}...")
    else:
        import redis
        redis_client = redis.from_url(url, decode_responses=True, socket_connect_timeout=3)
        redis_client.ping()
        print(f"✅ Redis connected: {url[:45]}...")
except Exception as e:
    print(f"⚠️ Redis disabled: {e}")
    redis_client = None

def rate_limit(key: str, limit=5, window=300):
    if not redis_client:
        return True
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, window)
        return count <= limit
    except:
        return True
