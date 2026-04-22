from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core import middleware as middleware_module


class DummyLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[tuple, dict]] = []
        self.warning_calls: list[tuple[tuple, dict]] = []
        self.exception_calls: list[tuple[tuple, dict]] = []

    def info(self, *args, **kwargs) -> None:
        self.info_calls.append((args, kwargs))

    def warning(self, *args, **kwargs) -> None:
        self.warning_calls.append((args, kwargs))

    def exception(self, *args, **kwargs) -> None:
        self.exception_calls.append((args, kwargs))


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(middleware_module.PublicFormRateLimitMiddleware)
    app.add_middleware(middleware_module.RequestLoggingMiddleware)

    @app.get("/health")
    def health(request: Request) -> dict[str, str]:
        return {"request_id": request.state.request_id}

    @app.post("/api/v1/public/tickets")
    def create_public_ticket() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_request_logging_adds_request_id_and_logs_completion(monkeypatch) -> None:
    dummy_logger = DummyLogger()

    monkeypatch.setattr(
        middleware_module,
        "settings",
        SimpleNamespace(
            API_V1_PREFIX="/api/v1",
            PUBLIC_FORM_RATE_LIMIT=5,
            PUBLIC_FORM_RATE_WINDOW_SECONDS=300,
        ),
    )
    monkeypatch.setattr(middleware_module, "rate_limiter", middleware_module.InMemoryRateLimiter())
    monkeypatch.setattr(middleware_module, "logger", dummy_logger)

    app = _build_test_app()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert len(request_id) == 32
    assert response.json()["request_id"] == request_id

    assert len(dummy_logger.info_calls) == 1
    log_args, _ = dummy_logger.info_calls[0]
    assert log_args[0].startswith("request_completed")
    assert log_args[1] == request_id
    assert log_args[2] == "GET"
    assert log_args[3] == "/health"
    assert log_args[4] == 200


def test_in_memory_rate_limiter_releases_bucket_after_window(monkeypatch) -> None:
    fake_now = {"value": 1000.0}
    monkeypatch.setattr(middleware_module.time, "time", lambda: fake_now["value"])

    limiter = middleware_module.InMemoryRateLimiter()

    assert limiter.allow_request("public-form:test", limit=1, window_seconds=60) == (True, 0)

    fake_now["value"] = 1030.0
    assert limiter.allow_request("public-form:test", limit=1, window_seconds=60) == (False, 30)

    fake_now["value"] = 1060.0
    assert limiter.allow_request("public-form:test", limit=1, window_seconds=60) == (True, 0)


def test_public_form_rate_limit_uses_forwarded_ip_and_returns_429(monkeypatch) -> None:
    dummy_logger = DummyLogger()
    fake_now = {"value": 1000.0}

    monkeypatch.setattr(middleware_module.time, "time", lambda: fake_now["value"])
    monkeypatch.setattr(
        middleware_module,
        "settings",
        SimpleNamespace(
            API_V1_PREFIX="/api/v1",
            PUBLIC_FORM_RATE_LIMIT=1,
            PUBLIC_FORM_RATE_WINDOW_SECONDS=60,
        ),
    )
    monkeypatch.setattr(middleware_module, "rate_limiter", middleware_module.InMemoryRateLimiter())
    monkeypatch.setattr(middleware_module, "logger", dummy_logger)

    app = _build_test_app()

    with TestClient(app) as client:
        first_response = client.post(
            "/api/v1/public/tickets",
            headers={"X-Forwarded-For": "198.51.100.10, 10.0.0.1"},
        )
        second_response = client.post(
            "/api/v1/public/tickets",
            headers={"X-Forwarded-For": "198.51.100.11, 10.0.0.1"},
        )
        limited_response = client.post(
            "/api/v1/public/tickets",
            headers={"X-Forwarded-For": "198.51.100.10, 10.0.0.1"},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert limited_response.status_code == 429
    assert limited_response.headers["Retry-After"] == "60"
    assert limited_response.headers.get("X-Request-ID")
    assert limited_response.json() == {
        "detail": "Terlalu banyak percobaan. Silakan coba lagi beberapa saat.",
        "retry_after_seconds": 60,
    }

    assert len(dummy_logger.warning_calls) == 1
    warning_args, _ = dummy_logger.warning_calls[0]
    assert warning_args[0].startswith("rate_limited")
    assert warning_args[2] == "198.51.100.10"
    assert warning_args[3] == "/api/v1/public/tickets"
    assert warning_args[4] == 60
