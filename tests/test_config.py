import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_support_legacy_env_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_NAME", "Legacy SLA API")
    monkeypatch.setenv("API_V1_STR", "/legacy-api")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("POSTGRES_PASSWORD", "mysql-secret")

    settings = Settings(_env_file=None)

    assert settings.APP_NAME == "Legacy SLA API"
    assert settings.API_V1_PREFIX == "/legacy-api"
    assert settings.jwt_secret_key == "x" * 32
    assert settings.PROJECT_NAME == "Legacy SLA API"
    assert settings.API_V1_STR == "/legacy-api"
    assert settings.SECRET_KEY == "x" * 32


def test_settings_build_database_url_from_mysql_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("MYSQL_SERVER", "db.internal")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_DB", "ticketing")
    monkeypatch.setenv("MYSQL_USER", "ticketing_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "p@ss word")

    settings = Settings(_env_file=None)

    assert (
        settings.database_url
        == "mysql+pymysql://ticketing_user:p%40ss+word@db.internal:3306/ticketing"
    )


def test_settings_normalize_database_url_and_split_lists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost:3306/appdb")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        " http://localhost:5173 , https://frontend.example.com ",
    )
    monkeypatch.setenv("ALLOWED_HOSTS", " localhost , api.example.com ")
    monkeypatch.setenv("APP_BASE_URL", "https://frontend.example.com/")
    monkeypatch.setenv("UPLOAD_URL_PREFIX", "uploads")

    settings = Settings(_env_file=None)

    assert settings.database_url == "mysql+pymysql://user:pass@localhost:3306/appdb"
    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://frontend.example.com",
    ]
    assert settings.allowed_hosts == ["localhost", "api.example.com"]
    assert settings.upload_base_url == "https://frontend.example.com/uploads"


def test_settings_reject_short_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "short-secret")
    monkeypatch.setenv("MYSQL_PASSWORD", "mysql-secret")

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY harus minimal 32 karakter"):
        Settings(_env_file=None)


def test_settings_normalize_postgres_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://user:pass@db.prisma.io:5432/postgres?sslmode=require",
    )
    monkeypatch.setenv("STORAGE_BACKEND", "vercel_blob")
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "blob-token")

    settings = Settings(_env_file=None)

    assert (
        settings.database_url
        == "postgresql+psycopg://user:pass@db.prisma.io:5432/postgres?sslmode=require"
    )
    assert settings.STORAGE_BACKEND == "vercel_blob"
