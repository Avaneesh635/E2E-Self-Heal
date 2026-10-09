import pytest
from pydantic import ValidationError

from product_api.config import Settings


@pytest.mark.parametrize("value", ["info", "Debug", " warning "])
def test_log_level_accepts_any_casing(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("PRODUCT_API_LOG_LEVEL", value)

    settings = Settings(database_url="sqlite://")

    assert settings.log_level == value.strip().upper()


def test_log_level_rejects_an_unknown_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRODUCT_API_LOG_LEVEL", "nope")

    with pytest.raises(ValidationError, match="log_level"):
        Settings(database_url="sqlite://")
