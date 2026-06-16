from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from repopilot import __version__


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "RepoPilot"
    app_version: str = __version__
    environment: str = "development"
    log_level: str = "info"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REPOPILOT_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
