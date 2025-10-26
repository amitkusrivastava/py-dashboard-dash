import os
from pathlib import Path
from typing import Optional, Literal

from dotenv import dotenv_values
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# =========================
# Configuration (ENV-DRIVEN via Pydantic)
# =========================

class _EnvLoader:
    """Helper to preload layered .env files into os.environ.

    Real environment variables always win; we only set values that are not already present.
    Among files, precedence is (lowest to highest):
      .env  <  .env.dev  <  .env.{APP_ENV}  <  .env.local  <  .env.{APP_ENV}.local
    APP_ENV defaults to "development"; "dev" is an alias for "development".
    """

    @staticmethod
    def load() -> None:
        _app_env_raw = os.getenv("APP_ENV", "development").lower()
        _app_env = "development" if _app_env_raw in {"dev", "development"} else _app_env_raw
        project_root = Path(__file__).resolve().parent.parent
        env_files = [
            project_root / ".env",
            project_root / ".env.dev",
            project_root / f".env.{_app_env}",
            project_root / ".env.local",
            project_root / f".env.{_app_env}.local",
        ]
        merged: dict[str, str] = {}
        for p in env_files:
            if p.exists():
                vals = dotenv_values(p)
                if vals:
                    merged.update({k: v for k, v in vals.items() if v is not None})
        for k, v in merged.items():
            if k not in os.environ and v is not None:
                os.environ[k] = v


class Settings(BaseSettings):
    """Application settings read from environment and validated by Pydantic.

    We rely on `_EnvLoader.load()` to provide layered .env behavior, then Pydantic reads from os.environ.
    """

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    # App/UI
    app_title: str = Field(default="Enterprise Analytics Dashboard", alias="APP_TITLE")
    port: int = Field(default=8050, ge=1, le=65535, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")

    # Data source
    data_source: Literal["SYNTHETIC", "REST", "SQL"] = Field(default="SYNTHETIC", alias="DATA_SOURCE")
    api_base_url: str = Field(default="", alias="API_BASE_URL")
    db_url: str = Field(default="", alias="DB_URL")
    max_rows: int = Field(default=7000, ge=1, alias="MAX_ROWS")

    # Auth/JWT
    disable_auth: bool = Field(default=False, alias="DISABLE_AUTH")
    jwt_secret: str = Field(default="dev-secret", alias="JWT_SECRET")
    jwt_issuer: Optional[str] = Field(default=None, alias="JWT_ISSUER")
    jwt_audience: Optional[str] = Field(default=None, alias="JWT_AUDIENCE")

    # Cache
    cache_type: Literal["SimpleCache", "RedisCache"] = Field(default="SimpleCache", alias="CACHE_TYPE")
    cache_timeout_seconds: int = Field(default=24 * 60 * 60, ge=0, alias="CACHE_TIMEOUT_SECONDS")
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")

    @field_validator("data_source", mode="before")
    @classmethod
    def _upper_data_source(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

    @classmethod
    def from_env(cls) -> "Settings":
        # Preload layered env files, then let Pydantic read/validate from os.environ
        _EnvLoader.load()
        return cls()  # type: ignore[call-arg]


# Backward-compatible module-level constants via a singleton Settings
_settings = Settings.from_env()

APP_TITLE = _settings.app_title
DATA_SOURCE = _settings.data_source
API_BASE_URL = _settings.api_base_url
DB_URL = _settings.db_url
JWT_SECRET = _settings.jwt_secret
JWT_ISSUER = _settings.jwt_issuer
JWT_AUDIENCE = _settings.jwt_audience
DISABLE_AUTH = _settings.disable_auth
CACHE_TYPE = _settings.cache_type
CACHE_TIMEOUT_SECONDS = _settings.cache_timeout_seconds
MAX_ROWS = _settings.max_rows
REDIS_URL = _settings.redis_url
PORT = _settings.port
DEBUG = _settings.debug

# Public helper to get the Settings object when class-based access is preferred
get_settings = lambda: _settings
