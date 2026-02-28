"""structlog 기반 JSON 로깅."""
import structlog
import logging
import sys
from config.settings import BASE_DIR

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level),
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_DIR / "bot.log", encoding="utf-8"),
        ],
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if level == "DEBUG"
            else structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def get_logger(name: str):
    return structlog.get_logger(name)
