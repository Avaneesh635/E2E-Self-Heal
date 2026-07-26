"""Content-addressed implementation of ISnapshotStore.

Stores each snapshot payload under a hash of its content, so two snapshots with
identical payloads collapse to a single stored object (deduplication). A small
per-id reference maps each ``snapshot_id`` to the content hash it points at,
keeping the public ``ISnapshotStore`` contract intact while the physical layout
becomes diffable across snapshot sets.

On-disk layout under the workspace ``snapshots`` directory::

    snapshots/
      objects/
        <sha256>.json   # canonical, deduplicated content blob (no snapshot_id)
      refs/
        <snapshot_id>.ref   # single line: the content hash it resolves to

The ``snapshot_id`` is deliberately excluded from the hashed content: identical
captured responses saved under different ids share one object, which is what
makes the store dedupe "identical responses" rather than identical keys.
"""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import structlog

from app.shadow.interfaces import ISnapshotStore
from app.shadow.schemas import ShadowSnapshot
from app.shadow.snapshot_store import (
    SnapshotCorruptionError,
    SnapshotNotFoundError,
    SnapshotStoreError,
)
from app.shadow.workspace import ShadowWorkspace

logger = structlog.get_logger(__name__)

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class ContentAddressedSnapshotStore(ISnapshotStore):
    """Hash-keyed snapshot store that deduplicates identical payloads.

    Sits behind :class:`ISnapshotStore` and honors the same schema contract as
    :class:`~app.shadow.snapshot_store.SnapshotStore`: it accepts a
    :class:`ShadowSnapshot` or a schema-valid dict and returns a validated
    :class:`ShadowSnapshot`.
    """

    def __init__(self, workspace: ShadowWorkspace) -> None:
        self.workspace = workspace
        self.objects_dir = workspace.snapshots_dir / "objects"
        self.refs_dir = workspace.snapshots_dir / "refs"
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self.refs_dir.mkdir(parents=True, exist_ok=True)

    def _ref_path(self, snapshot_id: str) -> Path:
        """Return the reference file path for a snapshot id (traversal-safe).

        The filename is a sha256 of the full ``snapshot_id`` so distinct ids map
        to distinct refs (no collisions from stripping path components) while the
        hex digest keeps the path traversal-safe.
        """
        safe_id = hashlib.sha256(snapshot_id.encode("utf-8")).hexdigest()
        return self.refs_dir / f"{safe_id}.ref"

    def _object_path(self, content_hash: str) -> Path:
        """Return the object blob path for a content hash."""
        return self.objects_dir / f"{content_hash}.json"

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        """Write ``text`` to ``path`` atomically via a sibling temp file.

        The temp file is fully written, flushed, and fsync'd before being
        ``os.replace``'d onto the target, so a reader never observes a partial
        file. The temp file is removed if anything fails before the replace.
        """
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _to_content(data: Any) -> dict[str, Any]:
        """Validate input and reduce it to hashable content (without the id)."""
        if isinstance(data, ShadowSnapshot):
            snapshot = data
        elif isinstance(data, dict):
            try:
                snapshot = ShadowSnapshot(**data)
            except Exception as e:
                raise SnapshotStoreError(f"Invalid snapshot dict structure: {e}")
        else:
            raise SnapshotStoreError("Unsupported data type; expected ShadowSnapshot or dict")

        content = snapshot.model_dump()
        content.pop("snapshot_id", None)
        return content

    @staticmethod
    def _hash_content(content: dict[str, Any]) -> str:
        """Compute a stable sha256 over canonical JSON of the content."""
        canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def save_snapshot(self, snapshot_id: str, data: Any) -> None:
        """Store a snapshot by content hash and point ``snapshot_id`` at it."""
        content = self._to_content(data)
        content_hash = self._hash_content(content)
        object_path = self._object_path(content_hash)

        deduped = object_path.exists()
        if not deduped:
            try:
                serialized = json.dumps(content, sort_keys=True, indent=2)
                self._atomic_write_text(object_path, serialized)
            except Exception as e:
                raise SnapshotStoreError(f"Failed to write snapshot object to disk: {e}")

        try:
            self._atomic_write_text(self._ref_path(snapshot_id), content_hash)
        except Exception as e:
            raise SnapshotStoreError(f"Failed to write snapshot reference to disk: {e}")

        logger.info(
            "snapshot_saved",
            snapshot_id=snapshot_id,
            content_hash=content_hash,
            deduped=deduped,
        )

    def get_snapshot(self, snapshot_id: str) -> ShadowSnapshot:
        """Resolve ``snapshot_id`` to its content and return a ShadowSnapshot."""
        ref_path = self._ref_path(snapshot_id)
        if not ref_path.exists():
            logger.warning("snapshot_not_found", snapshot_id=snapshot_id)
            raise SnapshotNotFoundError(f"Snapshot '{snapshot_id}' does not exist.")

        content_hash = ref_path.read_text(encoding="utf-8").strip()
        if not _SHA256_HEX.match(content_hash):
            logger.exception(
                "snapshot_ref_invalid", snapshot_id=snapshot_id, content_hash=content_hash
            )
            raise SnapshotCorruptionError(
                f"Snapshot '{snapshot_id}' has an invalid content hash reference."
            )

        object_path = self._object_path(content_hash)
        if not object_path.exists():
            logger.exception(
                "snapshot_object_missing", snapshot_id=snapshot_id, content_hash=content_hash
            )
            raise SnapshotCorruptionError(
                f"Snapshot '{snapshot_id}' references missing object '{content_hash}'."
            )

        try:
            content = json.loads(object_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            logger.exception(
                "snapshot_object_corrupted", snapshot_id=snapshot_id, content_hash=content_hash
            )
            raise SnapshotCorruptionError(
                f"Failed to read or parse snapshot object '{content_hash}': {e}"
            ) from e

        try:
            return ShadowSnapshot(snapshot_id=snapshot_id, **content)
        except Exception as e:
            logger.exception(
                "snapshot_data_invalid", snapshot_id=snapshot_id, content_hash=content_hash
            )
            raise SnapshotCorruptionError(
                f"Snapshot data does not conform to ShadowSnapshot schema: {e}"
            )
