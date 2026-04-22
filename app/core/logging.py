import logging
import logging.config
import os

from app.core.config import settings


def _is_vercel_runtime() -> bool:
    return os.getenv("VERCEL") == "1" or bool(os.getenv("VERCEL_ENV"))


def _build_log_config(*, include_file_handler: bool) -> dict:
    handlers: dict[str, dict] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": settings.LOG_LEVEL,
            "formatter": "standard",
        },
    }
    root_handlers = ["console"]

    if include_file_handler:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.LOG_LEVEL,
            "formatter": "standard",
            "filename": f"{settings.LOG_DIR}/app.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        }
        root_handlers.append("file")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            },
        },
        "handlers": handlers,
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": root_handlers,
        },
    }


def setup_logging() -> None:
    include_file_handler = not _is_vercel_runtime()

    if include_file_handler:
        try:
            os.makedirs(settings.LOG_DIR, exist_ok=True)
        except OSError:
            include_file_handler = False

    if include_file_handler:
        try:
            logging.config.dictConfig(_build_log_config(include_file_handler=True))
            return
        except OSError:
            include_file_handler = False
        except ValueError as exc:
            if "Unable to configure handler 'file'" not in str(exc):
                raise
            include_file_handler = False

    logging.config.dictConfig(_build_log_config(include_file_handler=False))

    if _is_vercel_runtime():
        logging.getLogger(__name__).info(
            "File logging disabled in Vercel runtime; using console handler only.",
        )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
