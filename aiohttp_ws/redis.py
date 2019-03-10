import aioredis
import asyncio
import logging

from aioredis import RedisError

from .settings import redis_settings as settings

logger = logging.getLogger(__name__)

_redis = None


async def get_redis(loop=None):
    loop = loop or asyncio.get_event_loop()

    return await aioredis.create_redis_pool(
        (settings.HOST, settings.PORT),
        db=settings.DB,
        loop=loop,
        minsize=settings.MIN_POOL_SIZE,
        maxsize=settings.MAX_POOL_SIZE,
    )


async def get_redis_lazy(loop=None):
    global _redis

    if _redis is None or (_redis and _redis.closed):
        _redis = await get_redis(loop)

    return _redis


async def close_redis():
    global _redis
    try:
        _redis.close()
        await _redis.wait_closed()
    except (asyncio.CancelledError, aioredis.RedisError):
        pass

    _redis = None


class OpenPubSubChannel:
    __slots__ = ('name', 'channel', 'redis')

    def __init__(self, name):
        self.name = name
        self.channel = None
        self.redis = None

    async def __aenter__(self):
        self.redis = await get_redis_lazy()
        self.channel, *_ = await self.redis.subscribe(self.name)
        return self.channel

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if not self.redis.closed:
                await self.redis.unsubscribe(self.name)
        except RedisError:
            pass


open_pubsub_channel = OpenPubSubChannel
