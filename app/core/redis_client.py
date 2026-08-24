import os
from dotenv import load_dotenv
import redis

load_dotenv()

redis_client = None

try:
    url = os.getenv("REDIS_URL")
    if url:
        redis_client = redis.from_url(url, decode_responses=True, socket_connect_timeout=3)
        redis_client.ping()
        print(f"✅ Redis connected: {url[:40]}...")
    else:
        print("⚠️ REDIS_URL not set - running without Redis")
except Exception as e:
    print(f"⚠️ Redis disabled: {e}")
    redis_client = None
