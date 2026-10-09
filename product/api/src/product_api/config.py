"""Settings for the product API, read from ``PRODUCT_API_*`` environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. The database URL has no default so no credentials live in code."""

    model_config = SettingsConfigDict(env_prefix="PRODUCT_API_", env_file=".env")

    database_url: str
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
