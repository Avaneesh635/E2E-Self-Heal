from pathlib import Path

import pytest

from app.shadow import CleanupPolicy, ShadowConfig, ShadowWorkspace
from app.shadow.workspace import _OWNERSHIP_MARKER


def test_workspace_derives_all_paths_from_config(tmp_path):
    config = ShadowConfig(
        workspace_dir=str(tmp_path / "ws"),
        cache_dir="c",
        snapshots_dir="s",
        tmp_dir="t",
    )
    ws = ShadowWorkspace(config)

    assert ws.base_dir == (tmp_path / "ws").resolve()
    assert ws.cache_dir == ws.base_dir / "c"
    assert ws.snapshots_dir == ws.base_dir / "s"
    assert ws.tmp_dir == ws.base_dir / "t"


def test_workspace_creates_owned_directory_tree(tmp_path):
    ws = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path / "ws")))

    assert ws.base_dir.is_dir()
    assert (ws.base_dir / _OWNERSHIP_MARKER).is_file()
    assert ws.cache_dir.is_dir()
    assert ws.snapshots_dir.is_dir()
    assert ws.tmp_dir.is_dir()


def test_workspace_can_reuse_an_owned_root(tmp_path):
    config = ShadowConfig(workspace_dir=str(tmp_path / "ws"))
    first = ShadowWorkspace(config)
    snapshot = first.snapshot_path("saved.json")
    snapshot.write_text("persistent", encoding="utf-8")

    second = ShadowWorkspace(config)

    assert second.snapshot_path("saved.json").read_text(encoding="utf-8") == "persistent"


def test_workspace_rejects_reassigning_owned_directory_roles(tmp_path):
    root = tmp_path / "ws"
    original = ShadowWorkspace(
        ShadowConfig(
            workspace_dir=str(root),
            cache_dir="cache",
            snapshots_dir="persistent",
            tmp_dir="tmp",
        )
    )
    snapshot = original.snapshot_path("saved.json")
    snapshot.write_text("persistent", encoding="utf-8")

    with pytest.raises(ValueError, match="ownership marker"):
        ShadowWorkspace(
            ShadowConfig(
                workspace_dir=str(root),
                cache_dir="persistent",
                snapshots_dir="snapshots",
                tmp_dir="tmp",
            )
        )

    assert snapshot.read_text(encoding="utf-8") == "persistent"


@pytest.mark.parametrize(
    "dangerous_root",
    [Path("/"), Path.home()],
    ids=["filesystem-root", "home-directory"],
)
def test_workspace_rejects_dangerous_roots(dangerous_root: Path):
    with pytest.raises(ValueError):
        ShadowWorkspace(ShadowConfig(workspace_dir=str(dangerous_root)))


def test_workspace_rejects_repository_root(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / ".git").mkdir()

    with pytest.raises(ValueError, match="repository root"):
        ShadowWorkspace(ShadowConfig(workspace_dir=str(repository)))


def test_workspace_rejects_non_empty_unowned_directory(tmp_path):
    unowned = tmp_path / "unowned"
    unowned.mkdir()
    sentinel = unowned / "keep.txt"
    sentinel.write_text("do not delete", encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty unowned"):
        ShadowWorkspace(ShadowConfig(workspace_dir=str(unowned)))

    assert sentinel.read_text(encoding="utf-8") == "do not delete"
    assert not (unowned / _OWNERSHIP_MARKER).exists()


def test_workspace_claims_an_existing_empty_directory(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()

    workspace = ShadowWorkspace(ShadowConfig(workspace_dir=str(empty)))

    assert (workspace.base_dir / _OWNERSHIP_MARKER).is_file()


def test_workspace_rejects_artifact_directory_at_ownership_marker(tmp_path):
    root = tmp_path / "ws"

    with pytest.raises(ValueError, match="ownership marker"):
        ShadowWorkspace(
            ShadowConfig(workspace_dir=str(root), cache_dir=_OWNERSHIP_MARKER)
        )

    assert not root.exists()


def test_cleanup_never_keeps_all_workspace_artifacts(tmp_path):
    ws = ShadowWorkspace(
        ShadowConfig(workspace_dir=str(tmp_path / "ws"), cleanup_policy=CleanupPolicy.NEVER)
    )

    ws.cleanup(is_success=True)

    assert ws.cache_dir.exists()
    assert ws.snapshots_dir.exists()
    assert ws.tmp_dir.exists()


def test_cleanup_on_success_keeps_artifacts_on_failure(tmp_path):
    ws = ShadowWorkspace(
        ShadowConfig(workspace_dir=str(tmp_path / "ws"), cleanup_policy=CleanupPolicy.ON_SUCCESS)
    )

    ws.cleanup(is_success=False)

    assert ws.cache_dir.exists()
    assert ws.snapshots_dir.exists()
    assert ws.tmp_dir.exists()


def test_cleanup_on_success_removes_only_disposable_artifacts(tmp_path):
    ws = ShadowWorkspace(
        ShadowConfig(workspace_dir=str(tmp_path / "ws"), cleanup_policy=CleanupPolicy.ON_SUCCESS)
    )
    snapshot = ws.snapshot_path("saved.json")
    snapshot.write_text("persistent", encoding="utf-8")

    ws.cleanup(is_success=True)

    assert ws.base_dir.exists()
    assert (ws.base_dir / _OWNERSHIP_MARKER).exists()
    assert not ws.cache_dir.exists()
    assert snapshot.read_text(encoding="utf-8") == "persistent"
    assert not ws.tmp_dir.exists()


def test_cleanup_always_removes_only_disposable_artifacts(tmp_path):
    ws = ShadowWorkspace(
        ShadowConfig(workspace_dir=str(tmp_path / "ws"), cleanup_policy=CleanupPolicy.ALWAYS)
    )
    snapshot = ws.snapshot_path("saved.json")
    snapshot.write_text("persistent", encoding="utf-8")

    ws.cleanup(is_success=False)

    assert ws.base_dir.exists()
    assert not ws.cache_dir.exists()
    assert snapshot.exists()
    assert not ws.tmp_dir.exists()


def test_setup_dirs_recreates_disposable_directories_after_cleanup(tmp_path):
    ws = ShadowWorkspace(
        ShadowConfig(workspace_dir=str(tmp_path / "ws"), cleanup_policy=CleanupPolicy.ALWAYS)
    )
    ws.cleanup()

    ws.setup_dirs()

    assert ws.cache_dir.is_dir()
    assert ws.snapshots_dir.is_dir()
    assert ws.tmp_dir.is_dir()


def test_cleanup_rejects_tampered_ownership_marker_before_deleting(tmp_path):
    ws = ShadowWorkspace(
        ShadowConfig(workspace_dir=str(tmp_path / "ws"), cleanup_policy=CleanupPolicy.ALWAYS)
    )
    marker = ws.base_dir / _OWNERSHIP_MARKER
    marker.write_text("not-owned", encoding="utf-8")

    with pytest.raises(ValueError, match="ownership marker"):
        ws.cleanup()

    assert ws.cache_dir.exists()
    assert ws.tmp_dir.exists()


def test_cleanup_rejects_symlinked_disposable_directory(tmp_path):
    ws = ShadowWorkspace(
        ShadowConfig(workspace_dir=str(tmp_path / "ws"), cleanup_policy=CleanupPolicy.ALWAYS)
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("do not delete", encoding="utf-8")
    ws.cache_dir.rmdir()
    ws.cache_dir.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError):
        ws.cleanup()

    assert sentinel.read_text(encoding="utf-8") == "do not delete"
    assert ws.tmp_dir.exists()


def test_cleanup_validates_all_targets_before_deleting(tmp_path):
    ws = ShadowWorkspace(
        ShadowConfig(workspace_dir=str(tmp_path / "ws"), cleanup_policy=CleanupPolicy.ALWAYS)
    )
    ws.tmp_dir.rmdir()
    ws.tmp_dir.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ValueError, match="not a directory"):
        ws.cleanup()

    assert ws.cache_dir.exists()


def test_shadow_workspace_helper_paths_use_expected_directories(tmp_path):
    workspace = ShadowWorkspace(
        ShadowConfig(
            workspace_dir=str(tmp_path / "shadow"),
            cache_dir="c",
            snapshots_dir="s",
            tmp_dir="t",
        )
    )

    assert workspace.cache_path("trace.zip") == workspace.base_dir / "c" / "trace.zip"
    assert workspace.snapshot_path("state.json") == workspace.base_dir / "s" / "state.json"
    assert workspace.tmp_path("run/output.txt") == workspace.base_dir / "t" / "run" / "output.txt"


def test_shadow_workspace_paths_reject_parent_traversal(tmp_path):
    workspace = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path / "shadow")))

    with pytest.raises(ValueError):
        workspace.resolve_path("../outside")
    with pytest.raises(ValueError):
        workspace.cache_path("../outside-cache")


def test_resolve_path_rejects_symlink_escape(tmp_path):
    workspace = ShadowWorkspace(ShadowConfig(workspace_dir=str(tmp_path / "shadow")))
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace.base_dir / "escape").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError):
        workspace.resolve_path("escape/file.txt")
