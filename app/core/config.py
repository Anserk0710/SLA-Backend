from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(value: str) -> str:
    if value.startswith("postgresql+"):
        return value

    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)

    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)

    return value


class Settings(BaseSettings):
    if TYPE_CHECKING:
        # Nilai settings dimuat dari env/.env saat runtime.
        # Stub ini membantu static type checker agar Settings() valid.
        def __init__(self, **values: Any) -> None: ...

    PROJECT_NAME: str = "SLA"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str
    DATABASE_URL: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "Boom@0710"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ticketing-SLA"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    FIRST_SUPERUSER_EMAIL: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin123"

    CLOUDINARY_CLOUD_NAME: str = "dkgxoiwtl"
    CLOUDINARY_API_KEY: str = "389353841874536"
    CLOUDINARY_API_SECRET: str = "LXb1UiXu9VeT6d-RBasZWBK9cjI"
    CLOUDINARY_FOLDER: str = "ticketting"

    MAX_IMAGE_UPLOAD_MB: int = 10
    MAX_VIDEO_UPLOAD_MB: int = 100

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY harus minimal 32 karakter")
        return value

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL:
            return _normalize_database_url(self.DATABASE_URL)

        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+psycopg://{user}:{password}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def uses_supabase_transaction_pooler(self) -> bool:
        database_url = self.sqlalchemy_database_url
        return "pooler.supabase.com:6543" in database_url
    
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
