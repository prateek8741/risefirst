"""Settings, read from environment variables (or backend/.env). Validated at startup."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/risefirst"
    sources_file: Path = _REPO_ROOT / "config" / "sources.yaml"

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    ai_call_budget: int = Field(default=300, ge=0, description="Max AI calls per ingestion run")
    ai_concurrency: int = Field(default=4, ge=1, le=16)
    # Free tier allows 5/min. Raise this once billing is enabled on the Google project.
    ai_requests_per_minute: float = Field(default=5, ge=0)

    http_timeout_seconds: float = 20.0
    cors_origins: list[str] = ["http://localhost:3000"]

    # Daily refresh: hour of day (in IST) when the scheduler runs ingestion.
    refresh_hour_ist: int = Field(default=6, ge=0, le=23)

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, url: str) -> str:
        """Hosted Postgres (Neon, Render) hands out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @property
    def ai_enabled(self) -> bool:
        return self.gemini_api_key is not None and bool(self.gemini_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
