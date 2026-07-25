"""Failed Test Registry: aggregate failure-stats data model (Issue #122)."""

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
    by_selector_pattern: dict[str, int] = Field(default_factory=dict)


class AggregateFailureStats(BaseModel):
    """Aggregate failure statistics across multiple healing records."""

    components: dict[str, ComponentFailureStats] = Field(default_factory=dict)
    total_records: int = 0
    global_by_cause: dict[FailureCause, int] = Field(default_factory=dict)
    global_by_selector_kind: dict[SelectorKind, int] = Field(default_factory=dict)
    global_by_selector_pattern: dict[str, int] = Field(default_factory=dict)


class HealingRecord(BaseModel):
    """
    A single healing history record (as read from the v0.5.5 healing-history store).
    """

    test_script_path: str
    component: str
    original_selector: str
    replacement_selector: str
    reason: str


def classify_selector_kind(selector: str) -> SelectorKind:
    """Heuristically classify a selector string into a SelectorKind."""
    selector = selector.strip().lower()
    if selector.startswith(("#", "[id=")):
        return SelectorKind.CSS_ID
    if selector.startswith((".", "[class=")):
        return SelectorKind.CSS_CLASS
    if selector.startswith(("[data-testid=", "[data-test=")):
        return SelectorKind.TEST_ID
    if selector.startswith(("role=", "getbyrole")):
        return SelectorKind.ROLE
    if selector.startswith(("//", ".xpath")):
        return SelectorKind.XPATH
    if selector.startswith(("text=", "getbytext")):
        return SelectorKind.TEXT
    return SelectorKind.OTHER


def classify_failure_cause(reason: str) -> FailureCause:
    """Heuristically classify a failure reason into a FailureCause."""
    reason = reason.lower()
    if "id" in reason or "rename" in reason:
        return FailureCause.ID_RENAME
    if "class" in reason or "classname" in reason or "style" in reason:
        return FailureCause.CLASSNAME_CHANGE
    if "text" in reason or "label" in reason or "content" in reason:
        return FailureCause.TEXT_CHANGE
    if "structur" in reason or "dom" in reason or "nest" in reason:
        return FailureCause.STRUCTURAL_CHANGE
    return FailureCause.OTHER


def aggregate_failure_stats(records: list[HealingRecord]) -> AggregateFailureStats:
    """
    Deterministically aggregate a list of healing records into failure statistics.
    Sorting ensures deterministic dictionary insertion order (Python 3.7+).
    """
    stats = AggregateFailureStats()

    # Sort by component, then reason, then original_selector for strict determinism
    sorted_records = sorted(records, key=lambda r: (r.component, r.reason, r.original_selector))

    for record in sorted_records:
        stats.total_records += 1

        cause = classify_failure_cause(record.reason)
        kind = classify_selector_kind(record.original_selector)
        pattern = record.original_selector  # Track the exact selector pattern

        # Global aggregation
        stats.global_by_cause[cause] = stats.global_by_cause.get(cause, 0) + 1
        stats.global_by_selector_kind[kind] = stats.global_by_selector_kind.get(kind, 0) + 1
        stats.global_by_selector_pattern[pattern] = (
            stats.global_by_selector_pattern.get(pattern, 0) + 1
        )

        # Component aggregation
        if record.component not in stats.components:
            stats.components[record.component] = ComponentFailureStats(
                component=record.component,
                total_failures=0,
                by_cause={},
                by_selector_kind={},
                by_selector_pattern={},
            )

        comp_stats = stats.components[record.component]
        comp_stats.total_failures += 1
        comp_stats.by_cause[cause] = comp_stats.by_cause.get(cause, 0) + 1
        comp_stats.by_selector_kind[kind] = comp_stats.by_selector_kind.get(kind, 0) + 1
        comp_stats.by_selector_pattern[pattern] = comp_stats.by_selector_pattern.get(pattern, 0) + 1

    return stats
