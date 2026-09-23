"""Project-wide logger. Import `logger` from this module anywhere in the app."""
import sys

from loguru import logger

from config import app_config

logger.remove()
logger.add(
    sys.stderr,
    level=app_config.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="14 days",
    level="DEBUG",
    enqueue=True,
)

__all__ = ["logger"]
