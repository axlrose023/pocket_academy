from dishka.integrations.taskiq import setup_dishka
from taskiq import SimpleRetryMiddleware
from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker

from config import get_config
from dependencies import get_async_container
from utils import setup_logging

setup_logging()
config = get_config()

redis_async_result = RedisAsyncResultBackend(
    redis_url=str(config.redis.dsn),
)

broker = ListQueueBroker(url=str(config.redis.dsn)).with_middlewares(
    SimpleRetryMiddleware(default_retry_count=3),
)
broker.with_result_backend(redis_async_result)

container = get_async_container()
setup_dishka(container=container, broker=broker)
