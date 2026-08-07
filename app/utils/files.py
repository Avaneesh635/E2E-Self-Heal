"""Filesystem helpers."""

import os
import tempfile
from pathlib import Path

from app.sandbox import assert_write_allowed


def split_line_ending(line: str) -> tuple[str, str]:
    """Return a line's content and its exact trailing line ending (``''`` if none).

    Handles ``\\r\\n``, ``\\n`` and lone ``\\r`` so callers preserve the original file's
    line endings instead of silently normalizing CRLF to LF.
    """
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith(("\n", "\r")):
        return line[:-1], line[-1:]
    return line, ""


def _fsync_parent_directory(path: Path) -> None:
    """Persist the directory entry after an atomic replacement where supported."""
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(path.parent, flags)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically and durably.

    Writes to a temp file in the same directory, syncs its contents, replaces the target,
    then syncs the parent directory so a crash mid-write cannot leave a half-patched file
    or lose the durable rename on supported platforms.
    """
    assert_write_allowed(path, reason="atomic_write")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        _fsync_parent_directory(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
