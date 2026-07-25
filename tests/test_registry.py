"""Tests for the Failed Test Registry aggregation (Issue #122)."""


from app.registry import (
    FailureCause,
    HealingRecord,
    SelectorKind,
    aggregate_failure_stats,
    classify_failure_cause,
    classify_selector_kind,
)


def test_classify_selector_kind():
    assert classify_selector_kind("#submit-btn") == SelectorKind.CSS_ID
    assert classify_selector_kind(".btn-primary") == SelectorKind.CSS_CLASS
    assert classify_selector_kind("[data-testid='login']") == SelectorKind.TEST_ID
    assert classify_selector_kind("role=button[name='Submit']") == SelectorKind.ROLE
    assert classify_selector_kind("//div[@id='main']") == SelectorKind.XPATH
    assert classify_selector_kind("text='Click me'") == SelectorKind.TEXT
    assert classify_selector_kind("div > span") == SelectorKind.OTHER


def test_classify_failure_cause():
    assert classify_failure_cause("button id was renamed") == FailureCause.ID_RENAME
    assert classify_failure_cause("className changed to primary") == FailureCause.CLASSNAME_CHANGE
    assert classify_failure_cause("text content updated") == FailureCause.TEXT_CHANGE
    assert classify_failure_cause("dom structure changed") == FailureCause.STRUCTURAL_CHANGE
    assert classify_failure_cause("unknown error") == FailureCause.OTHER


def test_aggregate_failure_stats_empty():
    stats = aggregate_failure_stats([])
    assert stats.total_records == 0
    assert stats.components == {}
    assert stats.global_by_cause == {}
    assert stats.global_by_selector_kind == {}
    assert stats.global_by_selector_pattern == {}


def test_aggregate_failure_stats_counts():
    records = [
        HealingRecord(
            test_script_path="tests/login.spec.ts",
            component="LoginButton",
            original_selector="#submit-btn",
            replacement_selector="#submit",
            reason="button id was renamed",
        ),
        HealingRecord(
            test_script_path="tests/login.spec.ts",
            component="LoginButton",
            original_selector="#submit-btn",
            replacement_selector="#submit",
            reason="button id was renamed",
        ),
        HealingRecord(
            test_script_path="tests/form.spec.ts",
            component="SubmitForm",
            original_selector=".btn-primary",
            replacement_selector="role=button[name='Submit']",
            reason="className changed to primary",
        ),
    ]
    
    stats = aggregate_failure_stats(records)
    
    assert stats.total_records == 3
    
    # Global counts
    assert stats.global_by_cause[FailureCause.ID_RENAME] == 2
    assert stats.global_by_cause[FailureCause.CLASSNAME_CHANGE] == 1
    assert stats.global_by_selector_kind[SelectorKind.CSS_ID] == 2
    assert stats.global_by_selector_kind[SelectorKind.CSS_CLASS] == 1
    
    # Global pattern tracking
    assert stats.global_by_selector_pattern["#submit-btn"] == 2
    assert stats.global_by_selector_pattern[".btn-primary"] == 1
    
    # Component counts
    assert len(stats.components) == 2
    assert "LoginButton" in stats.components
    assert stats.components["LoginButton"].total_failures == 2
    assert stats.components["LoginButton"].by_cause[FailureCause.ID_RENAME] == 2
    assert stats.components["LoginButton"].by_selector_kind[SelectorKind.CSS_ID] == 2
    assert stats.components["LoginButton"].by_selector_pattern["#submit-btn"] == 2
    
    assert "SubmitForm" in stats.components
    assert stats.components["SubmitForm"].total_failures == 1
    assert stats.components["SubmitForm"].by_cause[FailureCause.CLASSNAME_CHANGE] == 1
    assert stats.components["SubmitForm"].by_selector_kind[SelectorKind.CSS_CLASS] == 1
    assert stats.components["SubmitForm"].by_selector_pattern[".btn-primary"] == 1


def test_aggregate_failure_stats_deterministic_order():
    """Aggregation should produce the exact same result regardless of input order."""
    records1 = [
        HealingRecord(component="B", original_selector="x", replacement_selector="y", reason="z", test_script_path="a"),
        HealingRecord(component="A", original_selector="x", replacement_selector="y", reason="z", test_script_path="a"),
    ]
    records2 = [
        HealingRecord(component="A", original_selector="x", replacement_selector="y", reason="z", test_script_path="a"),
        HealingRecord(component="B", original_selector="x", replacement_selector="y", reason="z", test_script_path="a"),
    ]
    
    stats1 = aggregate_failure_stats(records1)
    stats2 = aggregate_failure_stats(records2)
    
    # Pydantic models compare by value, so this checks structural equality
    assert stats1 == stats2


def test_aggregate_failure_stats_tracks_selector_patterns():
    """Should track specific selector patterns, not just kinds."""
    records = [
        HealingRecord(
            test_script_path="tests/login.spec.ts",
            component="LoginButton",
            original_selector="#submit-btn",
            replacement_selector="#submit",
            reason="button id was renamed",
        ),
        HealingRecord(
            test_script_path="tests/login.spec.ts",
            component="LoginButton",
            original_selector="#submit-btn",  # Same pattern again
            replacement_selector="#submit",
            reason="button id was renamed",
        ),
        HealingRecord(
            test_script_path="tests/login.spec.ts",
            component="LoginButton",
            original_selector="#cancel-btn",  # Different pattern, same kind
            replacement_selector="#cancel",
            reason="button id was renamed",
        ),
        HealingRecord(
            test_script_path="tests/form.spec.ts",
            component="SubmitForm",
            original_selector=".btn-primary",
            replacement_selector="role=button[name='Submit']",
            reason="className changed to primary",
        ),
    ]
    
    stats = aggregate_failure_stats(records)
    
    # Global pattern tracking
    assert stats.global_by_selector_pattern["#submit-btn"] == 2
    assert stats.global_by_selector_pattern["#cancel-btn"] == 1
    assert stats.global_by_selector_pattern[".btn-primary"] == 1
    
    # Component pattern tracking
    assert stats.components["LoginButton"].by_selector_pattern["#submit-btn"] == 2
    assert stats.components["LoginButton"].by_selector_pattern["#cancel-btn"] == 1
    assert stats.components["SubmitForm"].by_selector_pattern[".btn-primary"] == 1
    
    # Kind tracking still works
    assert stats.global_by_selector_kind[SelectorKind.CSS_ID] == 3
    assert stats.global_by_selector_kind[SelectorKind.CSS_CLASS] == 1