"""Shadow Runtime module for E2E-Self-Heal.

Provides workspaces, snapshots, matching, and playwright mock injection.
"""

from app.shadow.browser_state import capture_browser_state, to_playwright_storage_state

from app.shadow.config import CleanupPolicy, MissPolicy, ShadowConfig
from app.shadow.injector import MockInjector
from app.shadow.in_memory_snapshot_store import InMemorySnapshotStore
from app.shadow.interfaces import (
    IMockInjector,
    IShadowRuntime,
    IShadowWorkspace,
    ISnapshotStore,
    ITraceParser,
)
from app.shadow.match_options import MatchOptions
from app.shadow.matcher import NoMatchError, SnapshotMatcher
from app.shadow.normalizer import RequestNormalizer
from app.shadow.runtime import ShadowRuntime
from app.shadow.schemas import (
    CapturedRequest,
    CapturedResponse,
    ClockSnapshot,
    CookieSnapshot,
    LocalStorageSnapshot,
    NetworkSnapshot,
    ShadowRunResult,
    ShadowSnapshot,
    StateSnapshot,
)
from app.shadow.scoring import MatchScorer, ScoringWeights
from app.shadow.snapshot_store import (
    SnapshotCorruptionError,
    SnapshotNotFoundError,
    SnapshotStore,
    SnapshotStoreError,
)
from app.shadow.trace_parser import (
    InvalidTraceArchiveError,
    PlaywrightTraceParser,
    TraceParseError,
)
from app.shadow.har_parser import HarTraceParser, InvalidHarFileError
from app.shadow.workspace import ShadowWorkspace

__all__ = [
    "IMockInjector",
    "IShadowRuntime",
    "IShadowWorkspace",
    "ISnapshotStore",
    "ITraceParser",
    "CleanupPolicy",
    "MissPolicy",
    "MockInjector",
    "capture_browser_state",
    "to_playwright_storage_state",
    "ShadowConfig",
    "ShadowRuntime",
    "SnapshotMatcher",
    "NoMatchError",
    "MatchOptions",
    "RequestNormalizer",
    "MatchScorer",
    "ScoringWeights",
    "CapturedRequest",
    "CapturedResponse",
    "ClockSnapshot",
    "CookieSnapshot",
    "LocalStorageSnapshot",
    "NetworkSnapshot",
    "StateSnapshot",
    "ShadowSnapshot",
    "ShadowRunResult",
    "SnapshotStore",
    "SnapshotStoreError",
    "SnapshotNotFoundError",
    "SnapshotCorruptionError",
    "PlaywrightTraceParser",
    "HarTraceParser",
    "TraceParseError",
    "InvalidTraceArchiveError",
    "InvalidHarFileError",
    "ShadowWorkspace",
    "InMemorySnapshotStore",
    "ContentAddressedSnapshotStore",
]
