from redis.asyncio import Redis
from src.config.settings import get_settings
from functools import lru_cache

_redis: Redis = None
settings = get_settings()

@lru_cache
def get_redis_client() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis



async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None