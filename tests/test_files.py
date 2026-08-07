from pathlib import Path

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


def test_atomic_write_fsyncs_before_replace(tmp_path, monkeypatch):
    import app.utils.files as files

    target = tmp_path / "sample.spec.ts"
    events = []
    real_fsync = files.os.fsync
    real_replace = files.os.replace

    def record_fsync(fd):
        events.append("fsync")
        return real_fsync(fd)

    def record_replace(source, destination):
        events.append(("replace", Path(source).exists()))
        return real_replace(source, destination)

    monkeypatch.setattr(files.os, "fsync", record_fsync)
    monkeypatch.setattr(files.os, "replace", record_replace)

    atomic_write(target, "durable")

    assert events == ["fsync", ("replace", True)]
    assert target.read_text() == "durable"
