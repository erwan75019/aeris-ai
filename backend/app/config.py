"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings with safe local defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AERIS_",
        extra="ignore",
    )

    app_name: str = "AERIS AI"
    app_version: str = "0.1.0"
    environment: str = "development"
    data_provider: str = "demo"
    database_url: str | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    opensky_client_id: str | None = None
    opensky_client_secret: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_provider and self.llm_model)


@lru_cache
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""

    return Settings()
