from yzconfig import YzConfig


class Settings(YzConfig):
    PUBSUB_CHANNEL_NAME = 'aiows'

    HEARTBEAT = 30
    AUTOPING = True

    CAMEL_CASE_TRANSFORM = True


class RedisSettings(YzConfig):
    HOST = None
    PORT = 6379
    DB = 0

    MIN_POOL_SIZE = 1
    MAX_POOL_SIZE = 10

    def _check_settings(self):
        assert self.HOST, "REDIS_HOST is empty"


settings = Settings('AIOWS_')
redis_settings = RedisSettings('AIOWS_REDIS_')
