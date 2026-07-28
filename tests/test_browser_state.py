"""End-to-end coverage for Playwright browser-state capture and replay."""

from datetime import datetime, timezone

from typing import Any

import pytest

from app.shadow.browser_state import capture_browser_state, to_playwright_storage_state
from app.shadow.config import ShadowConfig
from app.shadow.schemas import (
    ClockSnapshot,
    CookieSnapshot,
    LocalStorageSnapshot,
    ShadowSnapshot,
)
from app.shadow.snapshot_store import SnapshotStore
from app.shadow.workspace import ShadowWorkspace


class FakeBrowserContext:
    def __init__(self, storage_state: dict[str, Any]) -> None:
        self._storage_state = storage_state

    def storage_state(self) -> dict[str, Any]:
        return self._storage_state


def test_local_storage_capture_persist_load_and_replay(tmp_path) -> None:
    context = FakeBrowserContext(
        {
            "cookies": [],
            "origins": [
                {
                    "origin": "https://app.example.com",
                    "localStorage": [
                        {"name": "theme", "value": "dark"},
                        {"name": "feature_flags", "value": '{"checkout":true}'},
                    ],
                }
            ],
        }
    )

    captured = capture_browser_state(context)
    assert captured == [
        LocalStorageSnapshot(
            origin="https://app.example.com",
            items={"theme": "dark", "feature_flags": '{"checkout":true}'},
        )
    ]

    workspace = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path)))
    store = SnapshotStore(workspace)
    store.save_snapshot(
        "stateful",
        ShadowSnapshot(snapshot_id="stateful", state_snapshots=captured),
    )

    loaded = store.get_snapshot("stateful")
    assert to_playwright_storage_state(loaded.state_snapshots) == {
        "cookies": [],
        "origins": [
            {
                "origin": "https://app.example.com",
                "localStorage": [
                    {"name": "feature_flags", "value": '{"checkout":true}'},
                    {"name": "theme", "value": "dark"},
                ],
            }
        ],
    }


def test_cookie_capture_round_trips_playwright_field_names() -> None:
    context = FakeBrowserContext(
        {
            "cookies": [
                {
                    "name": "session",
                    "value": "token",
                    "domain": ".example.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                    "partitionKey": "https://top-level.example",
                }
            ],
            "origins": [],
        }
    )

    captured = capture_browser_state(context)
    assert isinstance(captured[0], CookieSnapshot)
    assert to_playwright_storage_state(captured) == context.storage_state()


def test_empty_or_schema_only_state_does_not_seed_playwright() -> None:
    assert to_playwright_storage_state([]) is None
    assert (
        to_playwright_storage_state(
            [ClockSnapshot(fixed_at=datetime(2026, 7, 28, tzinfo=timezone.utc))]
        )
        is None
    )


@pytest.mark.parametrize(
    "storage_state",
    [
        {"cookies": {}, "origins": []},
        {"cookies": [], "origins": [{"origin": "https://app.example.com", "localStorage": {}}]},
        {
            "cookies": [],
            "origins": [
                {
                    "origin": "https://app.example.com",
                    "localStorage": [{"name": "theme", "value": 42}],
                }
            ],
        },
    ],
)
def test_capture_rejects_malformed_playwright_state(storage_state: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        capture_browser_state(FakeBrowserContext(storage_state))
