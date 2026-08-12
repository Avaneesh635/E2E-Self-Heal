"""Tests for SnapshotStore."""

import json

import pytest

from app.shadow.config import ShadowConfig
from app.shadow.schemas import CapturedRequest, CapturedResponse, NetworkSnapshot, ShadowSnapshot
from app.shadow.snapshot_store import (
    SnapshotCorruptionError,
    SnapshotNotFoundError,
    SnapshotStore,
    SnapshotStoreError,
)
from app.shadow.workspace import ShadowWorkspace


def test_save_and_load_shadow_snapshot(tmp_path):
    ws = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path)))
    store = SnapshotStore(ws)

    req = CapturedRequest(
        method="GET", url="https://api.example.com/test", headers={"Accept": "*/*"}
    )
    res = CapturedResponse(status=200, headers={"Content-Type": "text/plain"}, body="hello-world")
    net_snap = NetworkSnapshot(request=req, response=res)

    snap = ShadowSnapshot(
        snapshot_id="test_snap_1",
        metadata={"user": "tester", "env": "ci"},
        network_snapshots=[net_snap],
    )

    # Test saving
    store.save_snapshot("test_snap_1", snap)

    # Check path existence (filename is now hashed from the id)
    expected_file = store._get_snapshot_path("test_snap_1")
    assert expected_file.exists()

    # Test loading
    loaded_snap = store.get_snapshot("test_snap_1")
    assert loaded_snap.snapshot_id == "test_snap_1"
    assert loaded_snap.metadata == {"user": "tester", "env": "ci"}
    assert len(loaded_snap.network_snapshots) == 1
    assert loaded_snap.network_snapshots[0].request.url == "https://api.example.com/test"


def test_save_dict_and_load(tmp_path):
    ws = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path)))
    store = SnapshotStore(ws)

    snapshot_dict = {
        "snapshot_id": "dict_snap",
        "metadata": {"source": "dict"},
        "network_snapshots": [],
        "state_snapshots": [],
    }

    store.save_snapshot("dict_snap", snapshot_dict)
    loaded_snap = store.get_snapshot("dict_snap")

    assert loaded_snap.snapshot_id == "dict_snap"
    assert loaded_snap.metadata == {"source": "dict"}


def test_save_invalid_dict_raises_error(tmp_path):
    ws = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path)))
    store = SnapshotStore(ws)

    # Dict with completely wrong fields (not just missing optional ones)
    bad_dict = {"wrong_field": "data", "another_bad_field": 123}

    try:
        store.save_snapshot("bad", bad_dict)
        assert False, "Should have raised SnapshotStoreError"
    except SnapshotStoreError as e:
        assert "Invalid snapshot dict structure" in str(e)


def test_save_unsupported_type_raises_error(tmp_path):
    ws = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path)))
    store = SnapshotStore(ws)

    try:
        store.save_snapshot("test", "not a dict or ShadowSnapshot")
        assert False, "Should have raised SnapshotStoreError"
    except SnapshotStoreError as e:
        assert "Unsupported data type" in str(e)


def test_get_snapshot_not_found(tmp_path):
    ws = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path)))
    store = SnapshotStore(ws)

    try:
        store.get_snapshot("nonexistent")
        assert False, "Should have raised SnapshotNotFoundError"
    except SnapshotNotFoundError as e:
        assert "does not exist" in str(e)


def test_get_snapshot_corrupted_json(tmp_path):
    ws = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path)))
    store = SnapshotStore(ws)

    # Write invalid JSON content manually at the hashed path
    corrupt_file = store._get_snapshot_path("corrupted")
    corrupt_file.write_text("{bad-json:", encoding="utf-8")

    with pytest.raises(SnapshotCorruptionError) as exc_info:
        store.get_snapshot("corrupted")

    assert "not valid JSON" in str(exc_info.value)


def test_get_snapshot_invalid_schema(tmp_path):
    ws = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path)))
    store = SnapshotStore(ws)

    # Write a valid JSON file but with incorrect fields that mismatch the Pydantic schema
    invalid_schema_file = store._get_snapshot_path("bad_schema")
    invalid_schema_file.write_text(json.dumps({"wrong_field": "data"}), encoding="utf-8")

    with pytest.raises(SnapshotCorruptionError) as exc_info:
        store.get_snapshot("bad_schema")

    assert "does not conform to ShadowSnapshot schema" in str(exc_info.value)
