"""Settings for the product API, read from ``PRODUCT_API_*`` environment variables."""

import logging
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. The database URL has no default so no credentials live in code."""

    model_config = SettingsConfigDict(env_prefix="PRODUCT_API_", env_file=".env")

    database_url: str
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        level = value.upper()
        valid_levels = logging.getLevelNamesMapping()
        if level not in valid_levels:
            raise ValueError(
                "PRODUCT_API_LOG_LEVEL must be one of: " + ", ".join(sorted(valid_levels))
            )
        return level


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
