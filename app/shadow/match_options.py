"""Configuration for request↔snapshot matching."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class MatchOptions:
    """Toggles that layer richer matching on top of the default scoring engine.

    Grouped by concern:

    * Query-param normalization — extend which params are dropped/normalized.
    * Header-aware matching — promote chosen headers to hard match requirements.
    * Body-aware matching — require an exact normalized body match.
    * Fuzzy / order-insensitive matching — compare JSON arrays as multisets.
    * Safety constraints — require matching origins and a minimum confidence.
    """

    # --- Query-param normalization (opt-in extensions) ---
    # Extra query keys to drop before comparison, beyond the built-in dynamic set.
    ignored_query_params: frozenset[str] = frozenset()
    # Lower-case query keys so ``?Tab=all`` and ``?tab=all`` normalize alike.
    case_insensitive_query_keys: bool = False

    # --- Header-aware matching (opt-in hard constraints) ---
    # Header names that MUST be present and equal on both sides; a candidate that
    # fails any required header is rejected outright (score -1.0). Compared on the
    # normalized (lower-cased key, scrubbed value) header maps.
    required_headers: frozenset[str] = frozenset()
    # Extra header names to ignore during scoring, beyond the built-in set.
    ignored_headers: frozenset[str] = frozenset()

    # --- Body-aware matching (opt-in hard constraint) ---
    # Reject candidates whose normalized body is not an exact match (score -1.0),
    # instead of merely scoring the body similarity.
    require_body_match: bool = False

    # --- Fuzzy / order-insensitive matching ---
    # Compare JSON arrays inside request bodies as multisets, so a reordered list
    # still matches. Off by default (arrays stay order-sensitive).
    order_insensitive_arrays: bool = False

    # --- Safety constraints ---
    # Permit matching requests across schemes, hosts, or effective ports. Off by
    # default so a captured response cannot leak to another origin accidentally.
    allow_cross_origin: bool = False
    # Inclusive score floor for accepting a candidate. A same-path request with
    # mismatched queries and otherwise empty metadata scores 170.
    min_score: float = 180.0

    def __post_init__(self) -> None:
        if not isfinite(self.min_score) or self.min_score < 0:
            raise ValueError("min_score must be a finite, non-negative number")
