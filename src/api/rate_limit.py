import hashlib
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from config import RateLimitConfig, RedisConfig

logger = logging.getLogger(__name__)

_INCREMENT_WITH_EXPIRY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


class RateLimiter:
    def __init__(self, *, redis: Redis, config: RateLimitConfig) -> None:
        self._redis = redis
        self._config = config
        self._is_available: bool | None = None

    @classmethod
    def from_config(
        cls, *, redis: RedisConfig, config: RateLimitConfig
    ) -> "RateLimiter":
        return cls(
            redis=Redis.from_url(str(redis.dsn), decode_responses=False),
            config=config,
        )

    async def allow(
        self,
        *,
        scope: str,
        identifier: str,
        limit: int,
    ) -> bool:
        if not self._config.enabled:
            return True
        key = self._key(scope=scope, identifier=identifier)
        try:
            count = int(
                await self._redis.eval(
                    _INCREMENT_WITH_EXPIRY,
                    1,
                    key,
                    self._config.window_seconds,
                )
            )
        except RedisError:
            if self._is_available is not False:
                logger.warning("Rate limiting is unavailable; allowing request")
            self._is_available = False
            return True
        self._is_available = True
        return count <= limit

    async def close(self) -> None:
        await self._redis.aclose()

    @staticmethod
    def _key(*, scope: str, identifier: str) -> str:
        fingerprint = hashlib.sha256(identifier.encode()).hexdigest()[:32]
        return f"pocket-academy:rate-limit:{scope}:{fingerprint}"
