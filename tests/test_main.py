from types import SimpleNamespace
from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main as main_module


class DummyLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[tuple, dict]] = []
        self.exception_calls: list[tuple[tuple, dict]] = []

    def info(self, *args, **kwargs) -> None:
        self.info_calls.append((args, kwargs))

    def exception(self, *args, **kwargs) -> None:
        self.exception_calls.append((args, kwargs))


def _build_settings(environment: str = "development") -> SimpleNamespace:
    return SimpleNamespace(
        APP_NAME="SLA Ticketing API",
        DEBUG=False,
        ENVIRONMENT=environment,
        API_V1_PREFIX="/api/v1",
        allowed_hosts=["testserver", "localhost", "127.0.0.1"],
        cors_origins=["http://localhost:5173"],
    )


def test_create_app_health_endpoint_returns_environment(monkeypatch) -> None:
    startup_called = {"value": False}
    dummy_logger = DummyLogger()

    def fake_init_db() -> SimpleNamespace:
        startup_called["value"] = True
        return SimpleNamespace(created_roles=0, created_users=0, updated_users=0)

    monkeypatch.setattr(main_module, "settings", _build_settings("staging"))
    monkeypatch.setattr(main_module, "init_db", fake_init_db)
    monkeypatch.setattr(main_module, "logger", dummy_logger)

    app = main_module.create_app()

    with TestClient(app) as client:
        response = client.get("/health")

    assert startup_called["value"] is True
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": "staging",
    }


def test_http_exception_handler_returns_request_id(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "settings", _build_settings())
    monkeypatch.setattr(
        main_module,
        "init_db",
        lambda: SimpleNamespace(created_roles=0, created_users=0, updated_users=0),
    )
    monkeypatch.setattr(main_module, "logger", DummyLogger())

    app = main_module.create_app()

    @app.get("/http-error")
    def http_error() -> None:
        raise HTTPException(status_code=418, detail="Teapot")

    with TestClient(app) as client:
        response = client.get("/http-error")

    assert response.status_code == 418
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert response.json() == {
        "detail": "Teapot",
        "request_id": request_id,
    }


def test_validation_exception_handler_returns_errors_and_request_id(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "settings", _build_settings())
    monkeypatch.setattr(
        main_module,
        "init_db",
        lambda: SimpleNamespace(created_roles=0, created_users=0, updated_users=0),
    )
    monkeypatch.setattr(main_module, "logger", DummyLogger())

    app = main_module.create_app()

    @app.get("/items/{item_id}")
    def read_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    with TestClient(app) as client:
        response = client.get("/items/not-a-number")

    assert response.status_code == 422
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    body = response.json()
    assert body["detail"] == "Validasi request gagal."
    assert body["request_id"] == request_id
    assert body["errors"]


def test_unhandled_exception_handler_returns_json_with_request_id(monkeypatch) -> None:
    dummy_logger = DummyLogger()

    monkeypatch.setattr(main_module, "settings", _build_settings())
    monkeypatch.setattr(
        main_module,
        "init_db",
        lambda: SimpleNamespace(created_roles=0, created_users=0, updated_users=0),
    )
    monkeypatch.setattr(main_module, "logger", dummy_logger)

    app = main_module.create_app()

    @app.get("/boom")
    def boom() -> None:
        raise ValueError("unexpected failure")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert response.json() == {
        "detail": "Terjadi kesalahan internal pada server.",
        "request_id": request_id,
    }
    assert len(dummy_logger.exception_calls) == 1


def test_create_app_adds_https_redirect_in_production(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "settings", _build_settings("production"))
    monkeypatch.setattr(
        main_module,
        "init_db",
        lambda: SimpleNamespace(created_roles=0, created_users=0, updated_users=0),
    )
    monkeypatch.setattr(main_module, "logger", DummyLogger())

    app = main_module.create_app()

    with TestClient(app) as client:
        response = client.get("/health", follow_redirects=False)

    assert response.status_code in {301, 307}
    assert response.headers["location"] == "https://testserver/health"


def test_create_app_mounts_local_uploads_when_enabled(monkeypatch, tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    uploaded_file = upload_dir / "proof.txt"
    uploaded_file.write_text("ok", encoding="utf-8")

    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            APP_NAME="SLA Ticketing API",
            DEBUG=False,
            ENVIRONMENT="development",
            API_V1_PREFIX="/api/v1",
            allowed_hosts=["testserver", "localhost", "127.0.0.1"],
            cors_origins=["http://localhost:5173"],
            uses_local_storage=True,
            upload_dir_path=upload_dir,
            UPLOAD_URL_PREFIX="/uploads",
        ),
    )
    monkeypatch.setattr(
        main_module,
        "init_db",
        lambda: SimpleNamespace(created_roles=0, created_users=0, updated_users=0),
    )
    monkeypatch.setattr(main_module, "logger", DummyLogger())

    app = main_module.create_app()

    with TestClient(app) as client:
        response = client.get("/uploads/proof.txt")

    assert response.status_code == 200
    assert response.text == "ok"
