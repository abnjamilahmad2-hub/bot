import redis.asyncio as redis
from redis.exceptions import ConnectionError
from shared.config import settings
import logging

logger = logging.getLogger("TS_BOT")

redis_client = redis.from_url(settings.redis_url, decode_responses=True)
_fallback_cache = {}

async def get_cache(key: str) -> str | None:
    try:
        return await redis_client.get(key)
    except ConnectionError:
        return _fallback_cache.get(key)
    except Exception as e:
        logger.error(f"Redis get error: {e}")
        return None

async def set_cache(key: str, value: str, expire: int = 3600):
    try:
        await redis_client.set(key, value, ex=expire)
    except ConnectionError:
        _fallback_cache[key] = value
    except Exception as e:
        logger.error(f"Redis set error: {e}")

async def delete_cache(key: str):
    try:
        await redis_client.delete(key)
    except ConnectionError:
        _fallback_cache.pop(key, None)
    except Exception as e:
        logger.error(f"Redis delete error: {e}")
