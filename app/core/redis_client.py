from functools import lru_cache
import redis
from .config import load_settings


@lru_cache
def get_redis() -> redis.Redis:
    settings = load_settings()
    client = redis.from_url(settings.redis.url, decode_responses=True)
    return client
