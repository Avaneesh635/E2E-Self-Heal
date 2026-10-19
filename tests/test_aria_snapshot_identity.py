"""Tests for test-identity-aware failure snapshot selection (Issue #223)."""

from pathlib import Path

from app.preprocess.aria_snapshot import read_failure_snapshot


def test_read_failure_snapshot_filters_by_test_path(tmp_path: Path) -> None:
    """When test_path is provided, only matching contexts are selected."""
    results_dir = tmp_path / "test-results"
    results_dir.mkdir()

    # Create two test result directories
    test_a_dir = results_dir / "spec-test-a"
    test_a_dir.mkdir()
    (test_a_dir / "error-context.md").write_text(
        "# Page snapshot\n```yaml\n- button: Submit A\n```"
    )

    test_b_dir = results_dir / "spec-test-b"
    test_b_dir.mkdir()
    (test_b_dir / "error-context.md").write_text(
        "# Page snapshot\n```yaml\n- button: Submit B\n```"
    )

    # Request snapshot for test A
    test_a_path = tmp_path / "tests" / "spec-test-a.ts"
    snapshot = read_failure_snapshot(results_dir, test_a_path)
    assert "Submit A" in snapshot
    assert "Submit B" not in snapshot


def test_read_failure_snapshot_no_match_returns_empty(tmp_path: Path) -> None:
    """When no context matches the test path, returns empty string."""
    results_dir = tmp_path / "test-results"
    results_dir.mkdir()

    # Create a result for a different test
    other_dir = results_dir / "spec-other"
    other_dir.mkdir()
    (other_dir / "error-context.md").write_text("# Page snapshot\n```yaml\n- button: Other\n```")

    # Request snapshot for a non-existent test
    test_path = tmp_path / "tests" / "spec-missing.ts"
    snapshot = read_failure_snapshot(results_dir, test_path)
    assert snapshot == ""


def test_read_failure_snapshot_handles_toctou(tmp_path: Path) -> None:
    """File deleted between glob and read returns empty string, not an exception."""
    results_dir = tmp_path / "test-results"
    results_dir.mkdir()

    test_dir = results_dir / "spec-test"
    test_dir.mkdir()
    context_file = test_dir / "error-context.md"
    context_file.write_text("# Page snapshot\n```yaml\n- button: Test\n```")

    test_path = tmp_path / "tests" / "spec-test.ts"

    # Delete the file before reading (simulates TOCTOU race)
    context_file.unlink()

    # Should return empty string, not raise FileNotFoundError
    snapshot = read_failure_snapshot(results_dir, test_path)
    assert snapshot == ""


def test_read_failure_snapshot_ambiguous_match_picks_newest(tmp_path: Path) -> None:
    """When multiple contexts match, picks the newest and logs warning."""
    results_dir = tmp_path / "test-results"
    results_dir.mkdir()

    # Create two directories that both match "spec"
    dir1 = results_dir / "spec-run-1"
    dir1.mkdir()
    file1 = dir1 / "error-context.md"
    file1.write_text("# Page snapshot\n```yaml\n- button: Run 1\n```")

    dir2 = results_dir / "spec-run-2"
    dir2.mkdir()
    file2 = dir2 / "error-context.md"
    file2.write_text("# Page snapshot\n```yaml\n- button: Run 2\n```")

    # Make file2 newer
    import time

    time.sleep(0.01)
    file2.write_text("# Page snapshot\n```yaml\n- button: Run 2\n```")

    test_path = tmp_path / "tests" / "spec.ts"
    snapshot = read_failure_snapshot(results_dir, test_path)

    # Should pick the newest
    assert "Run 2" in snapshot


def test_read_failure_snapshot_matches_truncated_directory_using_location(
    tmp_path: Path,
) -> None:
    """A truncated Playwright result directory still resolves by recorded location."""
    results_dir = tmp_path / "test-results"
    results_dir.mkdir()

    target_dir = results_dir / "catalog-pagination-regress-69aaf--to-the-second-catalog-page"
    target_dir.mkdir()
    (target_dir / "error-context.md").write_text(
        "# Test info\n"
        "- Name: catalog-pagination-regression/spec.ts >> advances to the second catalog page\n"
        "- Location: scenarios/catalog-pagination-regression/spec.ts:3:1\n\n"
        "# Page snapshot\n```yaml\n- button: Target\n```"
    )

    wrong_dir = results_dir / "spec-other-catalog-pagination-regress"
    wrong_dir.mkdir()
    (wrong_dir / "error-context.md").write_text(
        "# Test info\n"
        "- Name: catalog-pagination-other/spec.ts >> advances to the second catalog page\n"
        "- Location: scenarios/catalog-pagination-other/spec.ts:3:1\n\n"
        "# Page snapshot\n```yaml\n- button: Wrong test\n```"
    )

    snapshot = read_failure_snapshot(
        results_dir, Path("scenarios/catalog-pagination-regression/spec.ts")
    )

    assert "Target" in snapshot
    assert "Wrong test" not in snapshot
