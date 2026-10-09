from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog
from fastapi import FastAPI
from pydantic import ValidationError

from product_api.config import get_settings
from product_api.main import run


@pytest.fixture(autouse=True)
def settings_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PRODUCT_API_DATABASE_URL", "sqlite://")
    monkeypatch.delenv("PRODUCT_API_LOG_LEVEL", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_log_level_defaults_to_info() -> None:
    assert get_settings().log_level == "INFO"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("debug", "DEBUG"),
        ("info", "INFO"),
        ("warning", "WARNING"),
        ("error", "ERROR"),
        ("critical", "CRITICAL"),
        ("notset", "NOTSET"),
        ("warn", "WARN"),
        ("fatal", "FATAL"),
        ("iNfO", "INFO"),
        ("INFO", "INFO"),
    ],
)
def test_log_level_is_case_insensitive(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: str
) -> None:
    monkeypatch.setenv("PRODUCT_API_LOG_LEVEL", value)

    assert get_settings().log_level == expected


@pytest.mark.parametrize("value", ["nope", "INFOO", "", "20"])
def test_unknown_log_level_fails_when_settings_load(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("PRODUCT_API_LOG_LEVEL", value)

    with pytest.raises(ValidationError, match="PRODUCT_API_LOG_LEVEL") as exc:
        get_settings()

    assert exc.value.errors()[0]["loc"] == ("log_level",)


def test_api_starts_with_lowercase_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRODUCT_API_LOG_LEVEL", "info")
    logging_config = structlog.get_config()
    try:
        assert isinstance(run(), FastAPI)
    finally:
        structlog.configure(**logging_config)
