"""Translate between Playwright storage state and non-HTTP Shadow snapshots."""

from collections.abc import Iterable, Mapping
from typing import Any, Protocol, cast

from playwright.sync_api import StorageState

from app.shadow.schemas import (
    CookieSnapshot,
    LocalStorageSnapshot,
    StateSnapshot,
)


class SupportsStorageState(Protocol):
    """Minimal browser-context surface required for state capture."""

    def storage_state(self) -> dict[str, Any]:
        """Return Playwright-compatible browser storage state."""
        ...


def _mapping_items(value: object, field: str) -> list[Mapping[str, Any]]:
    """Validate a list of mapping objects returned by Playwright."""
    if not isinstance(value, list):
        raise ValueError(f"Playwright storage_state.{field} must be a list")
    if not all(isinstance(item, Mapping) for item in value):
        raise ValueError(f"Playwright storage_state.{field} entries must be objects")
    return value


def capture_browser_state(context: SupportsStorageState) -> list[StateSnapshot]:
    """Capture cookies and per-origin localStorage from a Playwright context."""
    storage_state = context.storage_state()
    if not isinstance(storage_state, dict):
        raise ValueError("Playwright storage_state must be an object")

    snapshots: list[StateSnapshot] = []
    for cookie in _mapping_items(storage_state.get("cookies", []), "cookies"):
        snapshots.append(
            CookieSnapshot.model_validate(
                {
                    "name": cookie.get("name"),
                    "value": cookie.get("value"),
                    "domain": cookie.get("domain"),
                    "path": cookie.get("path", "/"),
                    "expires": cookie.get("expires", -1.0),
                    "http_only": cookie.get("httpOnly", False),
                    "secure": cookie.get("secure", False),
                    "same_site": cookie.get("sameSite", "Lax"),
                    "partition_key": cookie.get("partitionKey"),
                }
            )
        )

    for origin_state in _mapping_items(storage_state.get("origins", []), "origins"):
        origin = origin_state.get("origin")
        entries = _mapping_items(origin_state.get("localStorage", []), "origins[].localStorage")
        items: dict[str, str] = {}
        for entry in entries:
            name = entry.get("name")
            value = entry.get("value")
            if not isinstance(name, str) or not isinstance(value, str):
                raise ValueError("Playwright localStorage names and values must be strings")
            items[name] = value
        snapshots.append(LocalStorageSnapshot.model_validate({"origin": origin, "items": items}))

    return snapshots


def to_playwright_storage_state(
    snapshots: Iterable[StateSnapshot],
) -> StorageState | None:
    """Build Playwright context storage state from supported Shadow snapshots.

    Clock snapshots remain schema-only until a clock replay adapter is added.
    """
    cookies: list[dict[str, Any]] = []
    local_storage_by_origin: dict[str, dict[str, str]] = {}

    for snapshot in snapshots:
        if isinstance(snapshot, CookieSnapshot):
            cookie: dict[str, Any] = {
                "name": snapshot.name,
                "value": snapshot.value,
                "domain": snapshot.domain,
                "path": snapshot.path,
                "expires": snapshot.expires,
                "httpOnly": snapshot.http_only,
                "secure": snapshot.secure,
                "sameSite": snapshot.same_site,
            }
            if snapshot.partition_key is not None:
                cookie["partitionKey"] = snapshot.partition_key
            cookies.append(cookie)
        elif isinstance(snapshot, LocalStorageSnapshot):
            local_storage_by_origin.setdefault(snapshot.origin, {}).update(snapshot.items)

    origins = [
        {
            "origin": origin,
            "localStorage": [
                {"name": name, "value": value}
                for name, value in sorted(local_storage_by_origin[origin].items())
            ],
        }
        for origin in sorted(local_storage_by_origin)
    ]

    if not cookies and not origins:
        return None
    return cast(StorageState, {"cookies": cookies, "origins": origins})
