"""Failed Test Registry: aggregate failure-stats data model (Issue #122)."""

import re
from enum import Enum

from pydantic import BaseModel, Field


class FailureCause(str, Enum):
    """Categorized reasons why a selector failed."""

    ID_RENAME = "id_rename"
    CLASSNAME_CHANGE = "classname_change"
    TEXT_CHANGE = "text_change"
    STRUCTURAL_CHANGE = "structural_change"
    OTHER = "other"


class SelectorKind(str, Enum):
    """Categorized types of CSS/DOM selectors."""

    CSS_ID = "css_id"
    CSS_CLASS = "css_class"
    ROLE = "role"
    TEST_ID = "test_id"
    XPATH = "xpath"
    TEXT = "text"
    OTHER = "other"


class ComponentFailureStats(BaseModel):
    """Failure statistics aggregated for a specific UI component."""

    component: str
    total_failures: int = 0
    by_cause: dict[FailureCause, int] = Field(default_factory=dict)
    by_selector_kind: dict[SelectorKind, int] = Field(default_factory=dict)


class AggregateFailureStats(BaseModel):
    """Aggregate failure statistics across multiple healing records."""

    components: dict[str, ComponentFailureStats] = Field(default_factory=dict)
    total_records: int = 0
    global_by_cause: dict[FailureCause, int] = Field(default_factory=dict)
    global_by_selector_kind: dict[SelectorKind, int] = Field(default_factory=dict)


class HealingRecord(BaseModel):
    """
    A single healing history record (as read from the v0.5.5 healing-history store).

    Note: This is a forward-looking design. Currently no code produces this structure.
    Integration requires a mapping layer from PatchInstruction + test metadata.
    """

    test_script_path: str
    component: str  # TODO: derive from test path or add to PatchInstruction
    original_selector: str
    replacement_selector: str
    reason: str


def classify_selector_kind(selector: str) -> SelectorKind:
    """Heuristically classify a selector string into a SelectorKind."""
    selector = selector.strip().lower()

    # Remove common prefixes like "page." or "locator."
    selector = re.sub(r"^(page|locator|expect)\.", "", selector)

    # Use tuples with str.startswith for cleaner, more efficient checks
    if selector.startswith(("xpath=", "//")):
        return SelectorKind.XPATH

    if selector.startswith(("#", "[id=")):
        return SelectorKind.CSS_ID

    # CSS class - but NOT .xpath (already handled above)
    if selector.startswith(("[class", "css=")) or (
        selector.startswith(".") and not selector.startswith(".xpath")
    ):
        return SelectorKind.CSS_CLASS

    if selector.startswith(("[data-testid=", "[data-test=", "getbytestid")):
        return SelectorKind.TEST_ID

    if selector.startswith(("role=", "getbyrole")):
        return SelectorKind.ROLE

    if selector.startswith(("text=", "getbytext", "getbylabel")):
        return SelectorKind.TEXT

    # Catch-all for other attribute selectors (e.g., "[name=...]", "[href=...]")
    if selector.startswith("["):
        return SelectorKind.CSS_CLASS

    return SelectorKind.OTHER


def classify_failure_cause(reason: str) -> FailureCause:
    """Heuristically classify a failure reason into a FailureCause using word boundaries."""
    reason = reason.lower()

    # Use word-boundary regexes for all checks to avoid false positives
    # ID rename: matches "id", "identifier" + change verbs
    if re.search(r"\b(id|identifier)\b", reason) and re.search(
        r"\b(renamed?|changed|updated|removed)\b", reason
    ):
        return FailureCause.ID_RENAME

    # Class name change: matches "class", "classname", "style" + change verbs
    if re.search(r"\b(class|classname|style)\b", reason) and re.search(
        r"\b(renamed?|changed|updated|removed)\b", reason
    ):
        return FailureCause.CLASSNAME_CHANGE

    # Text change: matches "text", "label", "content", "visible" + change verbs
    if re.search(r"\b(text|label|content|visible)\b", reason) and re.search(
        r"\b(renamed?|changed|updated|removed)\b", reason
    ):
        return FailureCause.TEXT_CHANGE

    # Structural change: matches "structur", "dom", "nest", "hierarch" OR "refactor", "restructur"
    if re.search(r"\b(structur|dom|nest|hierarch)\b", reason) or re.search(
        r"\b(refactor|restructur)\b", reason
    ):
        return FailureCause.STRUCTURAL_CHANGE

    return FailureCause.OTHER


def aggregate_failure_stats(records: list[HealingRecord]) -> AggregateFailureStats:
    """
    Deterministically aggregate a list of healing records into failure statistics.
    Sorting ensures deterministic dictionary insertion order (Python 3.7+).
    Final output is sorted by enum declaration order for stable JSON serialization.
    """
    stats = AggregateFailureStats()

    # Sort by component, then reason, then original_selector for strict determinism
    sorted_records = sorted(records, key=lambda r: (r.component, r.reason, r.original_selector))

    for record in sorted_records:
        stats.total_records += 1

        cause = classify_failure_cause(record.reason)
        kind = classify_selector_kind(record.original_selector)

        # Global aggregation
        stats.global_by_cause[cause] = stats.global_by_cause.get(cause, 0) + 1
        stats.global_by_selector_kind[kind] = stats.global_by_selector_kind.get(kind, 0) + 1

        # Component aggregation
        if record.component not in stats.components:
            stats.components[record.component] = ComponentFailureStats(
                component=record.component, total_failures=0, by_cause={}, by_selector_kind={}
            )

        comp_stats = stats.components[record.component]
        comp_stats.total_failures += 1
        comp_stats.by_cause[cause] = comp_stats.by_cause.get(cause, 0) + 1
        comp_stats.by_selector_kind[kind] = comp_stats.by_selector_kind.get(kind, 0) + 1

    # Sort global_by_cause and global_by_selector_kind by enum declaration order
    stats.global_by_cause = {
        cause: stats.global_by_cause[cause]
        for cause in FailureCause
        if cause in stats.global_by_cause
    }
    stats.global_by_selector_kind = {
        kind: stats.global_by_selector_kind[kind]
        for kind in SelectorKind
        if kind in stats.global_by_selector_kind
    }

    # Sort each component's stats the same way
    for comp_stats in stats.components.values():
        comp_stats.by_cause = {
            cause: comp_stats.by_cause[cause]
            for cause in FailureCause
            if cause in comp_stats.by_cause
        }
        comp_stats.by_selector_kind = {
            kind: comp_stats.by_selector_kind[kind]
            for kind in SelectorKind
            if kind in comp_stats.by_selector_kind
        }

    return stats
