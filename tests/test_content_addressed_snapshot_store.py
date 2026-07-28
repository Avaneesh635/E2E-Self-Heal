"""Tests for the content-addressed ISnapshotStore implementation."""

import pytest

from app import shadow
from app.shadow.config import ShadowConfig
from app.shadow.content_addressed_snapshot_store import ContentAddressedSnapshotStore
from app.shadow.interfaces import ISnapshotStore
from app.shadow.schemas import CapturedRequest, CapturedResponse, NetworkSnapshot, ShadowSnapshot
from app.shadow.snapshot_store import (
    SnapshotCorruptionError,
    SnapshotNotFoundError,
    SnapshotStoreError,
)
from app.shadow.workspace import ShadowWorkspace


def _make_store(tmp_path) -> ContentAddressedSnapshotStore:
    ws = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path)))
    return ContentAddressedSnapshotStore(ws)


def _make_snapshot(snapshot_id: str, body: str = "hello-world") -> ShadowSnapshot:
    req = CapturedRequest(
        method="GET", url="https://api.example.com/test", headers={"Accept": "*/*"}
    )
    res = CapturedResponse(status=200, headers={"Content-Type": "text/plain"}, body=body)
    net_snap = NetworkSnapshot(request=req, response=res)
    return ShadowSnapshot(
        snapshot_id=snapshot_id,
        metadata={"user": "tester", "env": "ci"},
        network_snapshots=[net_snap],
    )


def test_implements_isnapshot_store_interface(tmp_path):
    store = _make_store(tmp_path)
    assert isinstance(store, ISnapshotStore)


def test_content_addressed_store_is_publicly_exported() -> None:
    assert shadow.ContentAddressedSnapshotStore is ContentAddressedSnapshotStore


def test_save_and_get_shadow_snapshot_object(tmp_path):
    store = _make_store(tmp_path)

    store.save_snapshot("test_snap_1", _make_snapshot("test_snap_1"))
    loaded_snap = store.get_snapshot("test_snap_1")

    assert loaded_snap.snapshot_id == "test_snap_1"
    assert loaded_snap.metadata["user"] == "tester"
    assert len(loaded_snap.network_snapshots) == 1
    assert loaded_snap.network_snapshots[0].request.url == "https://api.example.com/test"
    assert loaded_snap.network_snapshots[0].response.body == "hello-world"


def test_save_dict_and_get_snapshot(tmp_path):
    store = _make_store(tmp_path)
    dict_data = {
        "snapshot_id": "test_snap_dict",
        "metadata": {"source": "manual"},
        "network_snapshots": [
            {
                "request": {
                    "method": "POST",
                    "url": "https://api.example.com/submit",
                    "headers": {},
                },
                "response": {"status": 201, "headers": {}, "body": "created"},
            }
        ],
    }

    store.save_snapshot("test_snap_dict", dict_data)
    loaded_snap = store.get_snapshot("test_snap_dict")

    assert loaded_snap.snapshot_id == "test_snap_dict"
    assert loaded_snap.network_snapshots[0].request.method == "POST"
    assert loaded_snap.network_snapshots[0].response.status == 201


def test_identical_payloads_map_to_one_object(tmp_path):
    """Two ids with identical content share a single stored object (dedup)."""
    store = _make_store(tmp_path)

    store.save_snapshot("snap_a", _make_snapshot("snap_a", body="same-body"))
    store.save_snapshot("snap_b", _make_snapshot("snap_b", body="same-body"))

    objects = list(store.objects_dir.glob("*.json"))
    refs = list(store.refs_dir.glob("*.ref"))

    # One deduplicated object, two references pointing at it.
    assert len(objects) == 1
    assert len(refs) == 2

    # Both ids resolve to the same content hash.
    hash_a = store._ref_path("snap_a").read_text(encoding="utf-8").strip()
    hash_b = store._ref_path("snap_b").read_text(encoding="utf-8").strip()
    assert hash_a == hash_b

    # Each id round-trips with its own identity preserved.
    assert store.get_snapshot("snap_a").snapshot_id == "snap_a"
    assert store.get_snapshot("snap_b").snapshot_id == "snap_b"


def test_differing_payloads_map_to_distinct_objects(tmp_path):
    store = _make_store(tmp_path)

    store.save_snapshot("snap_a", _make_snapshot("snap_a", body="body-one"))
    store.save_snapshot("snap_b", _make_snapshot("snap_b", body="body-two"))

    objects = list(store.objects_dir.glob("*.json"))
    assert len(objects) == 2


def test_saving_same_id_twice_updates_reference(tmp_path):
    store = _make_store(tmp_path)

    store.save_snapshot("snap", _make_snapshot("snap", body="first"))
    store.save_snapshot("snap", _make_snapshot("snap", body="second"))

    loaded = store.get_snapshot("snap")
    assert loaded.network_snapshots[0].response.body == "second"


def test_save_invalid_dict_raises_snapshot_store_error(tmp_path):
    store = _make_store(tmp_path)
    invalid_dict = {
        "snapshot_id": "invalid",
        "network_snapshots": [{"request": {"bad_field": True}}],  # Missing required fields
    }

    with pytest.raises(SnapshotStoreError) as exc_info:
        store.save_snapshot("invalid", invalid_dict)
    assert "Invalid snapshot dict structure" in str(exc_info.value)


def test_save_unsupported_type_raises_snapshot_store_error(tmp_path):
    store = _make_store(tmp_path)

    with pytest.raises(SnapshotStoreError) as exc_info:
        store.save_snapshot("unsupported", [1, 2, 3])  # type: ignore[arg-type]
    assert "Unsupported data type" in str(exc_info.value)


def test_get_snapshot_not_found_raises_error(tmp_path):
    store = _make_store(tmp_path)

    with pytest.raises(SnapshotNotFoundError) as exc_info:
        store.get_snapshot("does_not_exist")
    assert "does not exist" in str(exc_info.value)


def test_get_snapshot_dangling_reference_raises_corruption(tmp_path):
    store = _make_store(tmp_path)

    # A ref pointing at a valid-looking hash whose object was never written.
    store._ref_path("dangling").write_text("de" * 32, encoding="utf-8")

    with pytest.raises(SnapshotCorruptionError) as exc_info:
        store.get_snapshot("dangling")
    assert "missing object" in str(exc_info.value)


def test_get_snapshot_corrupted_object_raises_corruption(tmp_path):
    store = _make_store(tmp_path)

    store.save_snapshot("snap", _make_snapshot("snap"))
    content_hash = store._ref_path("snap").read_text(encoding="utf-8").strip()
    (store.objects_dir / f"{content_hash}.json").write_text("{bad-json:", encoding="utf-8")

    with pytest.raises(SnapshotCorruptionError) as exc_info:
        store.get_snapshot("snap")
    assert "Failed to read or parse snapshot object" in str(exc_info.value)
