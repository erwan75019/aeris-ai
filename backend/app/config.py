"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    data_provider: Literal["demo", "opensky"] = "demo"
    database_url: str | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    opensky_client_id: str | None = None
    opensky_client_secret: str | None = None
    aviation_weather_base_url: str = "https://aviationweather.gov/api/data"
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_base_url: str = "http://127.0.0.1:11434"
    llm_api_key: str | None = None
    anomaly_artifact_dir: Path = Path("artifacts/models/anomaly")
    trajectory_artifact_dir: Path = Path("artifacts/models/trajectory")
    density_artifact_dir: Path = Path("artifacts/models/density")

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_provider and self.llm_model)


@lru_cache
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""

    return Settings()
