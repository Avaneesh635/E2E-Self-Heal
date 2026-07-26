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


class ContentAddressedSnapshotStore(ISnapshotStore):
    """Hash-keyed snapshot store that deduplicates identical payloads.

    Sits behind :class:`ISnapshotStore` and honors the same schema contract as
    :class:`~app.shadow.snapshot_store.SnapshotStore`: it accepts a
    :class:`ShadowSnapshot` or a schema-valid dict and returns a validated
    :class:`ShadowSnapshot`.
    """

    def __init__(self, workspace: ShadowWorkspace):
        self.workspace = workspace
        self.objects_dir = workspace.snapshots_dir / "objects"
        self.refs_dir = workspace.snapshots_dir / "refs"
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self.refs_dir.mkdir(parents=True, exist_ok=True)

    def _ref_path(self, snapshot_id: str) -> Path:
        """Return the reference file path for a snapshot id (traversal-safe)."""
        safe_id = Path(snapshot_id).name
        return self.refs_dir / f"{safe_id}.ref"

    def _object_path(self, content_hash: str) -> Path:
        """Return the object blob path for a content hash."""
        return self.objects_dir / f"{content_hash}.json"

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
                object_path.write_text(serialized, encoding="utf-8")
            except Exception as e:
                raise SnapshotStoreError(f"Failed to write snapshot object to disk: {e}")

        try:
            self._ref_path(snapshot_id).write_text(content_hash, encoding="utf-8")
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
        except json.JSONDecodeError as e:
            logger.exception(
                "snapshot_object_corrupted", snapshot_id=snapshot_id, content_hash=content_hash
            )
            raise SnapshotCorruptionError(f"Snapshot object is not valid JSON: {e}")

        try:
            return ShadowSnapshot(snapshot_id=snapshot_id, **content)
        except Exception as e:
            logger.exception(
                "snapshot_data_invalid", snapshot_id=snapshot_id, content_hash=content_hash
            )
            raise SnapshotCorruptionError(
                f"Snapshot data does not conform to ShadowSnapshot schema: {e}"
            )
