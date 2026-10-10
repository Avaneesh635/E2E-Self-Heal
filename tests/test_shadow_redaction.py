import json
import stat

from app.shadow import (
    CapturedRequest,
    CapturedResponse,
    CookieSnapshot,
    LocalStorageSnapshot,
    NetworkSnapshot,
    ShadowConfig,
    ShadowSnapshot,
    ShadowWorkspace,
)
from app.shadow.har_parser import HarTraceParser
from app.shadow.redaction import redact_url, redact_value
from app.shadow.snapshot_store import SnapshotStore


def test_redact_url_removes_sensitive_query_values() -> None:
    safe = redact_url("https://example.test/data?page=2&token=secret")
    assert "secret" not in safe
    assert "page=2" in safe
    assert "token=%5BREDACTED%5D" in safe


def test_redact_value_removes_unstructured_credentials_and_url_components() -> None:
    safe = redact_value(
        "Authorization: Bearer test-token; password=test-password "
        "https://user:test-password@example.test/path#test-token"
    )

    assert safe == (
        "Authorization: Bearer [REDACTED]; password=[REDACTED] https://example.test/path#[REDACTED]"
    )


def test_snapshot_store_redacts_secrets_and_uses_private_permissions(tmp_path) -> None:
    workspace = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path / "shadow")))
    store = SnapshotStore(workspace)
    snapshot = ShadowSnapshot(
        snapshot_id="safe",
        network_snapshots=[
            NetworkSnapshot(
                request=CapturedRequest(
                    method="POST",
                    url="https://example.test/login?token=secret",
                    headers={"Authorization": "Bearer secret"},
                    body='{"password":"secret","name":"Ada"}',
                ),
                response=CapturedResponse(
                    status=200,
                    headers={"Set-Cookie": "session=secret"},
                    body='{"access_token":"secret","name":"Ada"}',
                ),
            )
        ],
        state_snapshots=[
            LocalStorageSnapshot(origin="https://example.test", items={"token": "secret"}),
            CookieSnapshot(name="session", value="secret", domain="example.test"),
        ],
    )

    store.save_snapshot("safe", snapshot)
    path = store._get_snapshot_path("safe")
    content = path.read_text()

    assert "secret" not in content
    assert "Ada" in content
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(content)["snapshot_id"] == "safe"


# --- repeated header names (#226) ---------------------------------------------------------


def _har_with_duplicate_response_headers(tmp_path) -> list[NetworkSnapshot]:
    har = {
        "log": {
            "entries": [
                {
                    "request": {
                        "method": "GET",
                        "url": "https://example.test/login",
                        "headers": [],
                    },
                    "response": {
                        "status": 200,
                        "headers": [
                            {"name": "Set-Cookie", "value": "session=first-secret; Path=/"},
                            {"name": "Set-Cookie", "value": "csrf=second-secret; Path=/"},
                            {"name": "Link", "value": "<a>; rel=preload"},
                            {"name": "Link", "value": "<b>; rel=preload"},
                            {"name": "Vary", "value": "Accept"},
                            {"name": "Vary", "value": "Origin"},
                        ],
                        "content": {"text": "ok"},
                    },
                }
            ]
        }
    }
    path = tmp_path / "duplicates.har"
    path.write_text(json.dumps(har), encoding="utf-8")
    return HarTraceParser().parse(path)


def test_duplicate_headers_survive_a_save_and_load_round_trip(tmp_path) -> None:
    store = SnapshotStore(ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path / "shadow"))))
    snapshot = ShadowSnapshot(
        snapshot_id="dupes", network_snapshots=_har_with_duplicate_response_headers(tmp_path)
    )

    store.save_snapshot("dupes", snapshot)
    headers = store.get_snapshot("dupes").network_snapshots[0].response.headers

    assert headers["Link"] == "<a>; rel=preload, <b>; rel=preload"
    assert headers["Vary"] == "Accept, Origin"


def test_redaction_removes_every_cookie_from_a_folded_set_cookie_header(tmp_path) -> None:
    store = SnapshotStore(ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path / "shadow"))))
    snapshot = ShadowSnapshot(
        snapshot_id="dupes", network_snapshots=_har_with_duplicate_response_headers(tmp_path)
    )

    store.save_snapshot("dupes", snapshot)
    content = store._get_snapshot_path("dupes").read_text()

    # The folded value is one header entry, so neither cookie can slip through.
    assert "first-secret" not in content
    assert "second-secret" not in content
    assert store.get_snapshot("dupes").network_snapshots[0].response.headers["Set-Cookie"] == (
        "[REDACTED]"
    )
