"""Validation tests for non-HTTP Shadow snapshot scopes."""

from datetime import datetime, timezone
from math import inf, nan

import pytest
from pydantic import ValidationError

from app.shadow.schemas import (
    ClockSnapshot,
    CookieSnapshot,
    LocalStorageSnapshot,
    ShadowSnapshot,
)


def test_local_storage_snapshot_validates_and_normalizes_origin() -> None:
    snapshot = LocalStorageSnapshot(
        origin="HTTPS://APP.EXAMPLE.COM:8443/",
        items={"theme": "dark", "session": "abc"},
    )

    assert snapshot.origin == "https://app.example.com:8443"
    assert snapshot.items == {"theme": "dark", "session": "abc"}


@pytest.mark.parametrize(
    "origin",
    [
        "ftp://app.example.com",
        "https://app.example.com/path",
        "https://app.example.com?tenant=one",
        "https://user:pass@app.example.com",
    ],
)
def test_local_storage_snapshot_rejects_non_origin_urls(origin: str) -> None:
    with pytest.raises(ValidationError):
        LocalStorageSnapshot(origin=origin)


def test_cookie_snapshot_validates_playwright_fields() -> None:
    cookie = CookieSnapshot(
        name="session",
        value="token",
        domain=".example.com",
        path="/app",
        expires=1_800_000_000,
        http_only=True,
        secure=True,
        same_site="Strict",
    )

    assert cookie.http_only is True
    assert cookie.same_site == "Strict"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("path", "app"),
        ("expires", -2),
        ("expires", nan),
        ("expires", inf),
        ("domain", "bad domain"),
        ("domain", "https://example.com"),
        ("domain", "example.com/path"),
        ("domain", "."),
        ("domain", "..example.com"),
        ("same_site", "Invalid"),
    ],
)
def test_cookie_snapshot_rejects_invalid_fields(field: str, value: object) -> None:
    data = {
        "name": "session",
        "value": "token",
        "domain": "example.com",
        field: value,
    }
    with pytest.raises(ValidationError):
        CookieSnapshot.model_validate(data)


def test_cookie_snapshot_requires_secure_for_same_site_none() -> None:
    with pytest.raises(ValidationError):
        CookieSnapshot(
            name="cross-site",
            value="token",
            domain="example.com",
            same_site="None",
            secure=False,
        )

    cookie = CookieSnapshot(
        name="cross-site",
        value="token",
        domain="example.com",
        same_site="None",
        secure=True,
    )
    assert cookie.secure is True


def test_clock_snapshot_requires_aware_time_and_valid_timezone() -> None:
    snapshot = ClockSnapshot(
        fixed_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
        timezone_id="Asia/Seoul",
    )
    assert snapshot.fixed_at.tzinfo is not None

    with pytest.raises(ValidationError):
        ClockSnapshot(fixed_at=datetime(2026, 7, 28), timezone_id="Asia/Seoul")
    with pytest.raises(ValidationError):
        ClockSnapshot(
            fixed_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
            timezone_id="Not/A_Timezone",
        )


def test_shadow_snapshot_deserializes_discriminated_state_scopes() -> None:
    snapshot = ShadowSnapshot.model_validate(
        {
            "snapshot_id": "stateful",
            "state_snapshots": [
                {
                    "scope": "local_storage",
                    "origin": "https://app.example.com",
                    "items": {"theme": "dark"},
                },
                {
                    "scope": "cookie",
                    "name": "session",
                    "value": "token",
                    "domain": "app.example.com",
                },
                {
                    "scope": "clock",
                    "fixed_at": "2026-07-28T00:00:00Z",
                    "timezone_id": "UTC",
                },
            ],
        }
    )

    assert isinstance(snapshot.state_snapshots[0], LocalStorageSnapshot)
    assert isinstance(snapshot.state_snapshots[1], CookieSnapshot)
    assert isinstance(snapshot.state_snapshots[2], ClockSnapshot)


def test_shadow_snapshot_rejects_unknown_state_scope() -> None:
    with pytest.raises(ValidationError):
        ShadowSnapshot.model_validate(
            {
                "snapshot_id": "unknown",
                "state_snapshots": [{"scope": "indexed_db", "items": {}}],
            }
        )


def test_legacy_http_only_snapshot_defaults_to_no_state() -> None:
    snapshot = ShadowSnapshot.model_validate({"snapshot_id": "legacy"})
    assert snapshot.state_snapshots == []
