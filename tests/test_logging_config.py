from pathlib import Path
from types import SimpleNamespace

from app.core import logging as logging_module


def test_setup_logging_builds_expected_config(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_makedirs(path: str, exist_ok: bool) -> None:
        captured["makedirs"] = {
            "path": path,
            "exist_ok": exist_ok,
        }

    def fake_dict_config(config: dict) -> None:
        captured["config"] = config

    monkeypatch.setattr(
        logging_module,
        "settings",
        SimpleNamespace(LOG_DIR=str(tmp_path), LOG_LEVEL="WARNING"),
    )
    monkeypatch.setattr(logging_module.os, "makedirs", fake_makedirs)
    monkeypatch.setattr(logging_module.logging.config, "dictConfig", fake_dict_config)

    logging_module.setup_logging()

    assert captured["makedirs"] == {
        "path": str(tmp_path),
        "exist_ok": True,
    }

    config = captured["config"]
    assert config["version"] == 1
    assert config["handlers"]["console"]["level"] == "WARNING"
    assert config["handlers"]["file"]["class"] == "logging.handlers.RotatingFileHandler"
    assert config["handlers"]["file"]["filename"] == f"{tmp_path}/app.log"
    assert config["handlers"]["file"]["backupCount"] == 5
    assert config["root"] == {
        "level": "WARNING",
        "handlers": ["console", "file"],
    }


def test_get_logger_returns_logger_by_name() -> None:
    logger = logging_module.get_logger("app.tests.logging")

    assert logger.name == "app.tests.logging"
