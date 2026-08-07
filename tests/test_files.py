from pathlib import Path

import pytest

from app.utils import files
from app.utils.files import atomic_write


def test_atomic_write_creates_and_overwrites(tmp_path):
    target = tmp_path / "sample.spec.ts"
    atomic_write(target, "first")
    assert target.read_text() == "first"
    atomic_write(target, "second")
    assert target.read_text() == "second"


def test_atomic_write_leaves_no_temp_files(tmp_path):
    target = tmp_path / "sample.spec.ts"
    atomic_write(target, "content")
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith(".tmp-")]
    assert leftovers == []


def test_atomic_write_fsyncs_file_before_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "sample.spec.ts"
    events: list[str] = []
    real_fsync = files.os.fsync
    real_replace = files.os.replace

    def record_fsync(fd: int) -> None:
        events.append("fsync")
        real_fsync(fd)

    def record_replace(source: Path, destination: Path) -> None:
        events.append("replace")
        real_replace(source, destination)

    monkeypatch.setattr(files.os, "fsync", record_fsync)
    monkeypatch.setattr(files.os, "replace", record_replace)

    atomic_write(target, "durable")

    # The file content must be synced before the rename; a final directory
    # fsync may follow the rename.
    assert events[:2] == ["fsync", "replace"]
    assert target.read_text() == "durable"


def test_atomic_write_fsyncs_parent_dir_after_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "sample.spec.ts"
    events: list[str] = []
    real_fsync = files.os.fsync
    real_replace = files.os.replace

    def record_fsync(fd: int) -> None:
        events.append("fsync")
        real_fsync(fd)

    def record_replace(source: Path, destination: Path) -> None:
        events.append("replace")
        real_replace(source, destination)

    monkeypatch.setattr(files.os, "fsync", record_fsync)
    monkeypatch.setattr(files.os, "replace", record_replace)

    atomic_write(target, "durable")

    assert events == ["fsync", "replace", "fsync"]
    assert target.read_text() == "durable"
