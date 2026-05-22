import redis.asyncio as redis
from shared.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)

async def get_cache(key: str) -> str | None:
    return await redis_client.get(key)

async def set_cache(key: str, value: str, expire: int = 3600):
    await redis_client.set(key, value, ex=expire)

async def delete_cache(key: str):
    await redis_client.delete(key)
