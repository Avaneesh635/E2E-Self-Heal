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
    """Test selector classification with expanded coverage."""
    # CSS ID
    assert classify_selector_kind("#submit-btn") == SelectorKind.CSS_ID
    assert classify_selector_kind("[id='submit']") == SelectorKind.CSS_ID

    # CSS Class
    assert classify_selector_kind(".btn-primary") == SelectorKind.CSS_CLASS
    assert classify_selector_kind("[class='btn']") == SelectorKind.CSS_CLASS

    # Test ID
    assert classify_selector_kind("[data-testid='login']") == SelectorKind.TEST_ID
    assert classify_selector_kind("[data-test='login']") == SelectorKind.TEST_ID
    assert classify_selector_kind("getByTestId('login')") == SelectorKind.TEST_ID

    # Role
    assert classify_selector_kind("role=button[name='Submit']") == SelectorKind.ROLE
    assert classify_selector_kind("getByRole('button')") == SelectorKind.ROLE
    assert classify_selector_kind("page.getByRole('button')") == SelectorKind.ROLE

    # XPath - NEW: support xpath= prefix
    assert classify_selector_kind("//div[@id='main']") == SelectorKind.XPATH
    assert classify_selector_kind("xpath=//div[@id='main']") == SelectorKind.XPATH

    # Text
    assert classify_selector_kind("text='Click me'") == SelectorKind.TEXT
    assert classify_selector_kind("getByText('Submit')") == SelectorKind.TEXT
    assert classify_selector_kind("getByLabel('Email')") == SelectorKind.TEXT

    # Attribute selectors
    assert classify_selector_kind("[class*=btn]") == SelectorKind.CSS_CLASS
    assert classify_selector_kind("css=#main") == SelectorKind.CSS_CLASS

    # Other
    assert classify_selector_kind("div > span") == SelectorKind.OTHER


def test_classify_selector_kind_not_reachable_branches():
    """Ensure .xpath is NOT matched as CSS class (was unreachable before fix)."""
    # This should be OTHER, not CSS_CLASS (the .xpath branch was unreachable)
    assert classify_selector_kind(".xpath(//div)") == SelectorKind.OTHER


def test_classify_failure_cause_no_false_positives():
    """Test that word-boundary regexes prevent false positives."""
    # These should NOT match (random words containing substrings)
    assert classify_failure_cause("element failed in random condition") == FailureCause.OTHER
    assert classify_failure_cause("changed in the context of the modal") == FailureCause.OTHER
    assert classify_failure_cause("the dom element") == FailureCause.OTHER  # "dom" alone

    # These SHOULD match (proper word boundaries)
    assert classify_failure_cause("button id was renamed") == FailureCause.ID_RENAME
    assert classify_failure_cause("className changed to primary") == FailureCause.CLASSNAME_CHANGE
    assert classify_failure_cause("text content updated") == FailureCause.TEXT_CHANGE
    assert classify_failure_cause("dom structure changed") == FailureCause.STRUCTURAL_CHANGE
    assert classify_failure_cause("refactored the component") == FailureCause.STRUCTURAL_CHANGE


def test_classify_failure_cause_expanded_verbs():
    """Test that expanded verbs are recognized."""
    # "removed" should work
    assert classify_failure_cause("the id attribute was removed") == FailureCause.ID_RENAME

    # "refactored" should work for structural
    assert classify_failure_cause("class was refactored") == FailureCause.STRUCTURAL_CHANGE

    # "changed" should work
    assert classify_failure_cause("data-testid changed") == FailureCause.ID_RENAME


def test_aggregate_failure_stats_empty():
    stats = aggregate_failure_stats([])
    assert stats.total_records == 0
    assert stats.components == {}
    assert stats.global_by_cause == {}
    assert stats.global_by_selector_kind == {}


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

    # Component counts
    assert len(stats.components) == 2
    assert "LoginButton" in stats.components
    assert stats.components["LoginButton"].total_failures == 2
    assert stats.components["LoginButton"].by_cause[FailureCause.ID_RENAME] == 2
    assert stats.components["LoginButton"].by_selector_kind[SelectorKind.CSS_ID] == 2

    assert "SubmitForm" in stats.components
    assert stats.components["SubmitForm"].total_failures == 1
    assert stats.components["SubmitForm"].by_cause[FailureCause.CLASSNAME_CHANGE] == 1
    assert stats.components["SubmitForm"].by_selector_kind[SelectorKind.CSS_CLASS] == 1


def test_aggregate_failure_stats_deterministic_order():
    """Aggregation should produce the exact same result regardless of input order."""
    records1 = [
        HealingRecord(
            component="B",
            original_selector="x",
            replacement_selector="y",
            reason="z",
            test_script_path="a",
        ),
        HealingRecord(
            component="A",
            original_selector="x",
            replacement_selector="y",
            reason="z",
            test_script_path="a",
        ),
    ]
    records2 = [
        HealingRecord(
            component="A",
            original_selector="x",
            replacement_selector="y",
            reason="z",
            test_script_path="a",
        ),
        HealingRecord(
            component="B",
            original_selector="x",
            replacement_selector="y",
            reason="z",
            test_script_path="a",
        ),
    ]

    stats1 = aggregate_failure_stats(records1)
    stats2 = aggregate_failure_stats(records2)

    # Pydantic models compare by value, so this checks structural equality
    assert stats1 == stats2

    # Check that component order is deterministic (sorted by component name)
    assert list(stats1.components.keys()) == ["A", "B"]
    assert list(stats2.components.keys()) == ["A", "B"]


def test_aggregate_failure_stats_enum_order_sorting():
    """Test that global_by_cause and global_by_selector_kind are sorted by enum declaration order."""
    records = [
        HealingRecord(
            component="Test",
            original_selector=".btn",
            replacement_selector="role=button",
            reason="text content changed",  # TEXT_CHANGE (3rd in enum)
            test_script_path="a",
        ),
        HealingRecord(
            component="Test",
            original_selector="#old",
            replacement_selector="#new",
            reason="id renamed",  # ID_RENAME (1st in enum)
            test_script_path="a",
        ),
    ]

    stats = aggregate_failure_stats(records)

    # Check that global_by_cause keys are in enum declaration order
    cause_keys = list(stats.global_by_cause.keys())
    expected_cause_order = [FailureCause.ID_RENAME, FailureCause.TEXT_CHANGE]
    assert cause_keys == expected_cause_order

    # Check that global_by_selector_kind keys are in enum declaration order
    kind_keys = list(stats.global_by_selector_kind.keys())
    expected_kind_order = [SelectorKind.CSS_CLASS, SelectorKind.ROLE]
    assert kind_keys == expected_kind_order


def test_aggregate_failure_stats_component_enum_sorting():
    """Test that component-level by_cause and by_selector_kind are sorted by enum order."""
    records = [
        HealingRecord(
            component="MyComponent",
            original_selector=".btn",
            replacement_selector="role=button",
            reason="text content changed",
            test_script_path="a",
        ),
        HealingRecord(
            component="MyComponent",
            original_selector="#old",
            replacement_selector="#new",
            reason="id renamed",
            test_script_path="a",
        ),
    ]

    stats = aggregate_failure_stats(records)

    comp_stats = stats.components["MyComponent"]

    # Check component's by_cause is in enum order
    assert list(comp_stats.by_cause.keys()) == [FailureCause.ID_RENAME, FailureCause.TEXT_CHANGE]

    # Check component's by_selector_kind is in enum order
    assert list(comp_stats.by_selector_kind.keys()) == [SelectorKind.CSS_CLASS, SelectorKind.ROLE]
