import logging
import sys

from config import get_config

config = get_config()


def setup_logging():
    logging_level = logging.DEBUG if config.bot.debug else logging.INFO
    logging.basicConfig(level=logging_level, stream=sys.stdout)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)

