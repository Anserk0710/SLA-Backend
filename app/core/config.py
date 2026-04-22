from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus, urljoin

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(value: str) -> str:
    normalized = value.strip()

    if normalized.startswith(("postgresql+", "mysql+pymysql://")):
        return normalized

    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+psycopg://", 1)

    if normalized.startswith("postgres://"):
        return normalized.replace("postgres://", "postgresql+psycopg://", 1)

    if normalized.startswith("mysql://"):
        return normalized.replace("mysql://", "mysql+pymysql://", 1)

    return normalized


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    if TYPE_CHECKING:
        # Nilai settings dimuat dari env/.env saat runtime.
        # Stub ini membantu static type checker agar Settings() valid.
        def __init__(self, **values: Any) -> None: ...

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = Field(
        default="SLA Ticketing API",
        validation_alias=AliasChoices("APP_NAME", "PROJECT_NAME"),
    )
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        validation_alias=AliasChoices("API_V1_PREFIX", "API_V1_STR"),
    )
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    DATABASE_URL: SecretStr | None = None
    JWT_SECRET_KEY: SecretStr = Field(
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"),
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    CORS_ORIGINS: str = "https://ptcahyaintanmedika.co.id"
    ALLOWED_HOSTS: str = "ptcahyaintanmedika.co.id"

    APP_BASE_URL: str = "https://ptcahyaintanmedika.co.id"
    PUBLIC_ROOT_DIR: str = "/home/u1563479/public_html"
    UPLOAD_DIR: str = "/home/u1563479/public_html/uploads"
    UPLOAD_URL_PREFIX: str = "/uploads"
    STORAGE_BACKEND: str = "local"

    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    PUBLIC_FORM_RATE_LIMIT: int = 5
    PUBLIC_FORM_RATE_WINDOW_SECONDS: int = 300

    MAX_IMAGE_UPLOAD_MB: int = 5
    MAX_VIDEO_UPLOAD_MB: int = 25

    MYSQL_SERVER: str = Field(
        default="localhost",
        validation_alias=AliasChoices("MYSQL_SERVER", "DB_HOST", "POSTGRES_SERVER"),
    )
    MYSQL_PORT: int = Field(
        default=3306,
        validation_alias=AliasChoices("MYSQL_PORT", "DB_PORT", "POSTGRES_PORT"),
    )
    MYSQL_DB: str = Field(
        default="ticketing_sla",
        validation_alias=AliasChoices("MYSQL_DB", "MYSQL_DATABASE", "DB_NAME", "POSTGRES_DB"),
    )
    MYSQL_USER: str = Field(
        default="ticketing_user",
        validation_alias=AliasChoices("MYSQL_USER", "MYSQL_USERNAME", "DB_USER", "POSTGRES_USER"),
    )
    MYSQL_PASSWORD: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "MYSQL_PASSWORD",
            "DB_PASSWORD",
            "POSTGRES_PASSWORD",
        ),
    )

    FIRST_SUPERUSER_EMAIL: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin123"

    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: SecretStr | None = None
    CLOUDINARY_API_SECRET: SecretStr | None = None
    CLOUDINARY_FOLDER: str = "ticketting"
    BLOB_READ_WRITE_TOKEN: SecretStr | None = None
    BLOB_ACCESS: str = "public"

    GEOAPIFY_REVERSE_GEOCODE_URL: str = "https://api.geoapify.com/v1/geocode/reverse"
    GEOAPIFY_API_KEY: str = ""
    GEOAPIFY_LANG: str = "id"

    @field_validator(
        "APP_NAME",
        "API_V1_PREFIX",
        "CORS_ORIGINS",
        "ALLOWED_HOSTS",
        "APP_BASE_URL",
        "PUBLIC_ROOT_DIR",
        "UPLOAD_DIR",
        "LOG_DIR",
        "BLOB_ACCESS",
        mode="before",
    )
    @classmethod
    def validate_trimmed_strings(cls, value: str) -> str:
        return value.strip()

    @field_validator(
        "DATABASE_URL",
        "MYSQL_PASSWORD",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
        "BLOB_READ_WRITE_TOKEN",
        mode="before",
    )
    @classmethod
    def validate_optional_secrets(cls, value: SecretStr | str | None) -> SecretStr | str | None:
        if value is None:
            return None

        if isinstance(value, SecretStr):
            normalized = value.get_secret_value().strip()
        else:
            normalized = value.strip()

        return normalized or None

    @field_validator("DEBUG", mode="before")
    @classmethod
    def validate_debug(cls, value: bool | str) -> bool:
        if isinstance(value, bool):
            return value

        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "production"}:
            return False
        raise ValueError("DEBUG harus bernilai boolean yang valid")

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"development", "staging", "production"}
        if normalized not in allowed:
            raise ValueError("ENVIRONMENT harus salah satu dari development, staging, production")
        return normalized

    @field_validator("APP_BASE_URL")
    @classmethod
    def validate_app_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized:
            raise ValueError("APP_BASE_URL tidak boleh kosong")
        return normalized

    @field_validator("UPLOAD_URL_PREFIX", mode="before")
    @classmethod
    def validate_upload_url_prefix(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return "/uploads"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized.rstrip("/") or "/uploads"

    @field_validator("STORAGE_BACKEND")
    @classmethod
    def validate_storage_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"local", "cloudinary", "vercel_blob"}
        if normalized not in allowed:
            raise ValueError("STORAGE_BACKEND harus salah satu dari local, cloudinary, atau vercel_blob")
        return normalized

    @field_validator("BLOB_ACCESS")
    @classmethod
    def validate_blob_access(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"public", "private"}
        if normalized not in allowed:
            raise ValueError("BLOB_ACCESS harus salah satu dari public atau private")
        return normalized

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY harus minimal 32 karakter")
        return value

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return _normalize_database_url(self.DATABASE_URL.get_secret_value())

        if self.MYSQL_PASSWORD is None:
            raise ValueError("MYSQL_PASSWORD wajib diisi jika DATABASE_URL tidak tersedia")

        user = quote_plus(self.MYSQL_USER)
        password = quote_plus(self.MYSQL_PASSWORD.get_secret_value())
        return (
            f"mysql+pymysql://{user}:{password}@"
            f"{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )

    @property
    def jwt_secret_key(self) -> str:
        return self.JWT_SECRET_KEY.get_secret_value()

    @property
    def cors_origins(self) -> list[str]:
        return _split_csv(self.CORS_ORIGINS)

    @property
    def allowed_hosts(self) -> list[str]:
        return _split_csv(self.ALLOWED_HOSTS)

    @property
    def cloudinary_api_key(self) -> str | None:
        if self.CLOUDINARY_API_KEY is None:
            return None
        return self.CLOUDINARY_API_KEY.get_secret_value()

    @property
    def cloudinary_api_secret(self) -> str | None:
        if self.CLOUDINARY_API_SECRET is None:
            return None
        return self.CLOUDINARY_API_SECRET.get_secret_value()

    @property
    def blob_read_write_token(self) -> str | None:
        if self.BLOB_READ_WRITE_TOKEN is None:
            return None
        return self.BLOB_READ_WRITE_TOKEN.get_secret_value()

    @property
    def mysql_password(self) -> str | None:
        if self.MYSQL_PASSWORD is None:
            return None
        return self.MYSQL_PASSWORD.get_secret_value()

    @property
    def sqlalchemy_database_url(self) -> str:
        return self.database_url

    @property
    def uses_supabase_transaction_pooler(self) -> bool:
        return "pooler.supabase.com:6543" in self.database_url

    @property
    def PROJECT_NAME(self) -> str:
        return self.APP_NAME

    @property
    def API_V1_STR(self) -> str:
        return self.API_V1_PREFIX

    @property
    def SECRET_KEY(self) -> str:
        return self.jwt_secret_key

    @property
    def cors_origins_list(self) -> list[str]:
        return self.cors_origins

    @property
    def public_root_dir_path(self) -> Path:
        return Path(self.PUBLIC_ROOT_DIR)

    @property
    def upload_dir_path(self) -> Path:
        return Path(self.UPLOAD_DIR)

    @property
    def upload_base_url(self) -> str:
        return urljoin(f"{self.APP_BASE_URL}/", self.UPLOAD_URL_PREFIX.lstrip("/"))

    @property
    def uses_local_storage(self) -> bool:
        return self.STORAGE_BACKEND == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
