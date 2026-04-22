import logging
import logging.config
import os

from app.core.config import settings


def setup_logging() -> None:
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "standard",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "standard",
                "filename": f"{settings.LOG_DIR}/app.log",
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console", "file"],
        },
    }

    logging.config.dictConfig(log_config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
