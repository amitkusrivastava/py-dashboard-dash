from pathlib import Path
from typing import Optional, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# =========================
# Configuration (ENV-DRIVEN via Pydantic)
# =========================


class Settings(BaseSettings):
    """Application settings read from environment and validated by Pydantic.

    Simplified: Only a single `.env` file at the project root is read. Real environment
    variables always take precedence over `.env` values. No layered env resolution.
    """

    # Read from .env at the project root; environment variables override.
    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
    )

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


# Singleton accessor to avoid repeated disk reads/parsing
_settings_singleton: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the singleton Settings instance, initializing it on first call."""
    global _settings_singleton
    if _settings_singleton is None:
        _settings_singleton = Settings()
    return _settings_singleton


# Convenience module-level constants used by app.py when running as a script
PORT: int = get_settings().port
DEBUG: bool = get_settings().debug
