import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import app.cli as cli_module
from app.cli import app
from app.config import settings
from app.safety_benchmark import (
    ActualOutcome,
    ExpectedOutcome,
    SafetyBenchmarkReport,
    SafetyScenario,
    SafetyScenarioResult,
    ScenarioClass,
    ScenarioRestoreError,
    build_report,
)
from app.safety_report import load_baseline, render_markdown

_DRIFT = (ScenarioClass.SELECTOR_DRIFT, ExpectedOutcome.REPAIR)
_REGRESSION = (ScenarioClass.PRODUCT_REGRESSION, ExpectedOutcome.REFUSE)


def _result(
    name: str,
    kind: tuple[ScenarioClass, ExpectedOutcome],
    actual: ActualOutcome,
    *,
    latency: float = 2,
    attempts: int | None = 1,
    error: str | None = None,
    refusal_reason: str | None = None,
    declined: int | None = None,
) -> SafetyScenarioResult:
    return SafetyScenarioResult(
        name=name,
        scenario_class=kind[0],
        expected_outcome=kind[1],
        actual_outcome=actual,
        latency_seconds=latency,
        attempts=attempts,
        declined=declined,
        error=error,
        refusal_reason=refusal_reason,
    )


def _report() -> SafetyBenchmarkReport:
    return build_report(
        [
            _result("id-rename", _DRIFT, ActualOutcome.REPAIR),
            _result("product-regression", _REGRESSION, ActualOutcome.REFUSE, attempts=3),
        ]
    )


def test_markdown_shows_metrics_with_their_sample_sizes() -> None:
    text = render_markdown(_report())

    assert text.startswith("# Safety benchmark\n")
    assert "| False-green rate (product regressions repaired) | 0.0% | 1 |" in text
    assert "| Correct-refusal rate (expected refusals refused) | 100.0% | 1 |" in text
    assert "**2 scored, 0 skipped, 0 errors**" in text


def test_markdown_lists_every_class_and_names_the_coverage_gaps() -> None:
    text = render_markdown(_report())

    for scenario_class in ScenarioClass:
        assert f"| `{scenario_class.value}` |" in text
    assert "## Coverage gaps" in text
    for empty in ("accessible_name_drift", "timing", "ambiguous", "environment"):
        assert f"`{empty}`" in text.split("## Coverage gaps")[1]
    # A class with scenarios is not reported as a gap.
    assert "`selector_drift`" not in text.split("## Coverage gaps")[1]


def test_markdown_states_that_cost_is_not_measured_rather_than_zero() -> None:
    text = render_markdown(_report())

    assert "Model cost: not measured" in text
    assert "$0" not in text


def test_markdown_renders_empty_rates_as_not_available() -> None:
    text = render_markdown(build_report([]))

    assert "| False-green rate (product regressions repaired) | n/a | 0 |" in text
    assert "**0 scored, 0 skipped, 0 errors**" in text


def test_markdown_reports_skipped_scenarios_without_scoring_them() -> None:
    report = build_report(
        [
            _result("static", _DRIFT, ActualOutcome.SKIPPED, latency=0, attempts=None),
            _result("id-rename", _DRIFT, ActualOutcome.REPAIR),
        ]
    )

    text = render_markdown(report)

    assert "**1 scored, 1 skipped, 0 errors**" in text
    assert "| `selector_drift` | 1 (+1 skipped) |" in text


def test_markdown_shows_why_a_scenario_was_refused() -> None:
    # A refusal is scored by outcome alone, so the reason is what reveals a correct refusal
    # that happened only because the engine ran out of attempts.
    report = build_report(
        [
            _result(
                "product-regression",
                _REGRESSION,
                ActualOutcome.REFUSE,
                refusal_reason="loop_cap_reached",
            ),
            _result("id-rename", _DRIFT, ActualOutcome.REPAIR),
        ]
    )

    text = render_markdown(report)

    assert "| Refusal reason |" in text
    assert "| refuse | `loop_cap_reached` |" in text
    assert "| repair | — |" in text


def test_markdown_separates_patches_proposed_from_declines() -> None:
    # The signature of the empty-patch loop: nothing proposed, several declines, refused at the cap.
    report = build_report(
        [
            _result(
                "product-regression",
                _REGRESSION,
                ActualOutcome.REFUSE,
                attempts=0,
                declined=3,
                refusal_reason="loop_cap_reached",
            ),
            _result("id-rename", _DRIFT, ActualOutcome.REPAIR, attempts=2, declined=0),
        ]
    )

    text = render_markdown(report)

    assert "| Attempts | Declined |" in text
    assert "| `loop_cap_reached` | 2.0 s | 0 | 3 |" in text
    assert "| repair | — | 2.0 s | 2 | 0 |" in text


def test_a_scenario_without_a_decline_count_renders_a_dash() -> None:
    # Errors and reports saved before the field existed have no count; not zero.
    report = build_report([_result("broken", _DRIFT, ActualOutcome.ERROR, attempts=None)])

    assert "| — | — |" in render_markdown(report)


def test_markdown_truncates_and_flattens_error_messages() -> None:
    long_error = "first line\n" + "x" * 400
    report = build_report([_result("broken", _DRIFT, ActualOutcome.ERROR, error=long_error)])

    section = render_markdown(report).split("## Errors")[1]

    assert "- `broken`: first line xxxx" in section
    assert "\n  " not in section.strip()
    assert section.strip().endswith("…")
    assert len(section.strip()) < 260


def test_baseline_deltas_flag_an_outcome_flip_a_new_and_a_removed_scenario() -> None:
    baseline = build_report(
        [
            _result("id-rename", _DRIFT, ActualOutcome.REPAIR, latency=2, attempts=1),
            _result("product-regression", _REGRESSION, ActualOutcome.REFUSE),
            _result("gone", _DRIFT, ActualOutcome.REPAIR),
        ]
    )
    current = build_report(
        [
            _result("id-rename", _DRIFT, ActualOutcome.REFUSE, latency=5, attempts=3),
            _result("product-regression", _REGRESSION, ActualOutcome.REFUSE),
            _result("fresh", _DRIFT, ActualOutcome.REPAIR),
        ]
    )

    text = render_markdown(current, baseline)

    assert "| **repair → refuse** |" in text
    assert "unchanged |" in text
    assert "| new |" in text
    assert "Removed since baseline: gone" in text
    assert "Baseline: 3 scenarios" in text


def test_baseline_deltas_show_metric_movement_in_percentage_points() -> None:
    baseline = build_report([_result("a", _DRIFT, ActualOutcome.REPAIR)])
    current = build_report(
        [
            _result("a", _DRIFT, ActualOutcome.REPAIR),
            _result("b", _DRIFT, ActualOutcome.REFUSE),
        ]
    )

    text = render_markdown(current, baseline)

    assert "Change vs baseline" in text
    # Incorrect refusals went from 0% of one expected repair to 50% of two.
    assert "| Incorrect-refusal rate (expected repairs refused) | 50.0% | 2 | +50.0 pp |" in text


def test_baseline_deltas_show_spend_tradeoffs() -> None:
    baseline = build_report([_result("a", _DRIFT, ActualOutcome.REPAIR, latency=2, attempts=1)])
    current = build_report([_result("a", _DRIFT, ActualOutcome.REPAIR, latency=5, attempts=3)])

    text = render_markdown(current, baseline)

    assert "Total latency: 5.0 s (+3.0 s)" in text
    assert "Mean repair attempts per scenario: 3.00 (+2.00)" in text


def test_class_row_shows_the_baseline_score_only_when_it_changed() -> None:
    baseline = build_report([_result("a", _DRIFT, ActualOutcome.REPAIR)])
    same = render_markdown(build_report([_result("a", _DRIFT, ActualOutcome.REPAIR)]), baseline)
    worse = render_markdown(build_report([_result("a", _DRIFT, ActualOutcome.REFUSE)]), baseline)

    assert "(was" not in same
    assert "0/1 (was 1/1)" in worse


# --- baseline loading ---------------------------------------------------------------


def test_a_missing_baseline_means_there_is_no_baseline_yet(tmp_path: Path) -> None:
    assert load_baseline(tmp_path / "absent.json") is None


def test_a_report_round_trips_as_a_baseline(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    report = _report()
    path.write_text(report.model_dump_json(indent=2))

    assert load_baseline(path) == report


def test_a_baseline_from_before_the_summaries_existed_still_loads(tmp_path: Path) -> None:
    # The first runner emitted only `results` and `metrics`. A committed baseline in that
    # shape must stay usable, so the new fields cannot be required.
    path = tmp_path / "old.json"
    path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "name": "id-rename",
                        "scenario_class": "selector_drift",
                        "expected_outcome": "repair",
                        "actual_outcome": "repair",
                        "latency_seconds": 1.5,
                    }
                ],
                "metrics": {
                    "false_green_rate": None,
                    "repair_precision": 1.0,
                    "correct_refusal_rate": None,
                    "incorrect_refusal_rate": 0.0,
                    "error_count": 0,
                },
            }
        )
    )

    baseline = load_baseline(path)

    assert baseline is not None
    assert [r.name for r in baseline.results] == ["id-rename"]
    text = render_markdown(_report(), baseline)
    assert "Baseline: 1 scenarios" in text


def test_an_invalid_baseline_is_an_error_not_silently_ignored(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"results": "nope"}')

    with pytest.raises(ValueError, match="not a valid safety report"):
        load_baseline(path)


# --- CLI ----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _default_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pin the policy so these tests do not depend on a developer's .env.
    monkeypatch.setattr(settings, "sandbox_mode", "relaxed")
    monkeypatch.setattr(settings, "write_globs", "*.spec.ts,**/*.spec.ts")


@pytest.fixture
def scenario_root(tmp_path: Path) -> Path:
    root = tmp_path / "scenarios"
    for name, kind, expected in (
        ("alpha", "selector_drift", "repair"),
        ("beta", "product_regression", "refuse"),
    ):
        directory = root / name
        directory.mkdir(parents=True)
        (directory / f"{name}.spec.ts").write_text("")
        (directory / "change.patch").write_text("")
        (directory / "meta.json").write_text(
            json.dumps(
                {
                    "class": kind,
                    "expected_outcome": expected,
                    "failing_selector": "#x",
                    "rationale": "A labeled scenario.",
                }
            )
        )
    return root


def _stub_executor(actual: ActualOutcome):
    def execute(scenario: SafetyScenario) -> SafetyScenarioResult:
        return _result(
            scenario.name,
            (scenario.scenario_class, scenario.expected_outcome),
            actual,
        )

    return execute


def test_cli_writes_the_json_and_markdown_files_and_exits_zero_regardless_of_scores(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path, tmp_path: Path
) -> None:
    # Every outcome is wrong (a false green and an incorrect refusal would both be here), but
    # gates are only enforced with --enforce-gates, so a completed run is never a failure.
    monkeypatch.setattr(cli_module, "execute_safety_scenario", _stub_executor(ActualOutcome.ERROR))
    json_out = tmp_path / "out" / "report.json"
    md_out = tmp_path / "out" / "report.md"

    result = CliRunner().invoke(
        app,
        [
            "safety-benchmark",
            "--scenario-root",
            str(scenario_root),
            "--output",
            str(json_out),
            "--markdown",
            str(md_out),
        ],
    )

    assert result.exit_code == 0
    written = SafetyBenchmarkReport.model_validate_json(json_out.read_text())
    assert [r.name for r in written.results] == ["alpha", "beta"]
    assert json_out.read_text().endswith("\n")
    assert md_out.read_text().startswith("# Safety benchmark\n")
    # stdout still carries the same report, as before the new options existed.
    assert SafetyBenchmarkReport.model_validate_json(result.stdout) == written


def test_cli_compares_against_a_baseline_in_the_markdown(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path, tmp_path: Path
) -> None:
    baseline = build_report(
        [
            _result("alpha", _DRIFT, ActualOutcome.REPAIR),
            _result("beta", _REGRESSION, ActualOutcome.REFUSE),
        ]
    )
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(baseline.model_dump_json())
    monkeypatch.setattr(cli_module, "execute_safety_scenario", _stub_executor(ActualOutcome.REPAIR))
    md_out = tmp_path / "report.md"

    result = CliRunner().invoke(
        app,
        [
            "safety-benchmark",
            "--scenario-root",
            str(scenario_root),
            "--markdown",
            str(md_out),
            "--baseline",
            str(baseline_path),
        ],
    )

    assert result.exit_code == 0
    assert "**refuse → repair**" in md_out.read_text()


def test_cli_treats_a_missing_baseline_as_none_and_says_so(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli_module, "execute_safety_scenario", _stub_executor(ActualOutcome.REPAIR))
    md_out = tmp_path / "report.md"

    result = CliRunner().invoke(
        app,
        [
            "safety-benchmark",
            "--scenario-root",
            str(scenario_root),
            "--markdown",
            str(md_out),
            "--baseline",
            str(tmp_path / "absent.json"),
        ],
    )

    assert result.exit_code == 0
    assert "no baseline at" in result.stderr
    assert "Baseline: none" in md_out.read_text()


def test_cli_rejects_an_invalid_baseline_before_running_anything(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        cli_module,
        "execute_safety_scenario",
        lambda scenario: pytest.fail("must not run with an unusable baseline"),
    )
    bad = tmp_path / "bad.json"
    bad.write_text("not json")

    result = CliRunner().invoke(
        app, ["safety-benchmark", "--scenario-root", str(scenario_root), "--baseline", str(bad)]
    )

    assert result.exit_code == 2
    # The console wraps long lines, so compare the message without its line breaks.
    assert "not a valid safety report" in " ".join(result.stderr.split())
    assert "pydantic.dev" not in result.stderr


def test_cli_uses_the_preparing_executor_only_when_asked(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path
) -> None:
    called: list[str] = []

    def prepared(scenario: SafetyScenario) -> SafetyScenarioResult:
        called.append(f"prepared:{scenario.name}")
        return _stub_executor(ActualOutcome.REPAIR)(scenario)

    def plain(scenario: SafetyScenario) -> SafetyScenarioResult:
        called.append(f"plain:{scenario.name}")
        return _stub_executor(ActualOutcome.REPAIR)(scenario)

    monkeypatch.setattr(cli_module, "execute_prepared_scenario", prepared)
    monkeypatch.setattr(cli_module, "execute_safety_scenario", plain)

    CliRunner().invoke(app, ["safety-benchmark", "--scenario-root", str(scenario_root)])
    CliRunner().invoke(
        app, ["safety-benchmark", "--scenario-root", str(scenario_root), "--apply-patches"]
    )

    assert called == ["plain:alpha", "plain:beta", "prepared:alpha", "prepared:beta"]


def test_cli_aborts_with_a_failure_when_the_working_tree_cannot_be_restored(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path, tmp_path: Path
) -> None:
    def broken(scenario: SafetyScenario) -> SafetyScenarioResult:
        raise ScenarioRestoreError("could not reverse change.patch")

    monkeypatch.setattr(cli_module, "execute_prepared_scenario", broken)
    json_out = tmp_path / "report.json"

    result = CliRunner().invoke(
        app,
        [
            "safety-benchmark",
            "--scenario-root",
            str(scenario_root),
            "--apply-patches",
            "--output",
            str(json_out),
        ],
    )

    assert result.exit_code == 1
    assert "working tree not restored" in result.stderr
    # A partial report from a run on a compromised tree must not be written.
    assert not json_out.exists()


def test_cli_fails_fast_when_the_sandbox_forbids_writing_scenario_files(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path
) -> None:
    # The demo scenarios are literally named spec.ts, which the default globs do not match.
    (scenario_root / "alpha" / "alpha.spec.ts").rename(scenario_root / "alpha" / "spec.ts")
    monkeypatch.setattr(
        cli_module,
        "execute_safety_scenario",
        lambda scenario: pytest.fail("nothing may run when no repair could be written"),
    )

    result = CliRunner().invoke(app, ["safety-benchmark", "--scenario-root", str(scenario_root)])

    assert result.exit_code == 2
    message = " ".join(result.stderr.split())
    assert "alpha" in message
    assert "E2E_HEALER_WRITE_GLOBS" in message


def test_cli_runs_when_the_write_globs_allow_spec_ts(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path
) -> None:
    (scenario_root / "alpha" / "alpha.spec.ts").rename(scenario_root / "alpha" / "spec.ts")
    monkeypatch.setattr(settings, "write_globs", "*.spec.ts,**/*.spec.ts,spec.ts,**/spec.ts")
    monkeypatch.setattr(cli_module, "execute_safety_scenario", _stub_executor(ActualOutcome.REPAIR))

    result = CliRunner().invoke(app, ["safety-benchmark", "--scenario-root", str(scenario_root)])

    assert result.exit_code == 0


def test_cli_rejects_a_missing_scenario_root(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app, ["safety-benchmark", "--scenario-root", str(tmp_path / "missing")]
    )

    assert result.exit_code == 2


def test_cli_enforce_gates_exits_one_on_a_false_green(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path, tmp_path: Path
) -> None:
    # beta is a product regression; repairing it is a false green, which fails at any n.
    monkeypatch.setattr(cli_module, "execute_safety_scenario", _stub_executor(ActualOutcome.REPAIR))
    md_out = tmp_path / "report.md"
    args = ["safety-benchmark", "--scenario-root", str(scenario_root), "--markdown", str(md_out)]

    informational = CliRunner().invoke(app, args)
    enforced = CliRunner().invoke(app, [*args, "--enforce-gates"])

    assert informational.exit_code == 0
    assert enforced.exit_code == 1
    assert "false_green_rate" in enforced.stderr
    assert "| `false_green_rate` | = 0% | 100.0% | 1 | **FAIL** |" in md_out.read_text()


def test_cli_enforce_gates_does_not_fail_on_an_insufficient_sample(
    monkeypatch: pytest.MonkeyPatch, scenario_root: Path
) -> None:
    # alpha (drift) is wrongly refused, but one scenario is far below the minimum sample.
    monkeypatch.setattr(cli_module, "execute_safety_scenario", _stub_executor(ActualOutcome.REFUSE))

    result = CliRunner().invoke(
        app, ["safety-benchmark", "--scenario-root", str(scenario_root), "--enforce-gates"]
    )

    assert result.exit_code == 0


def test_cli_rejects_a_scenario_without_metadata(scenario_root: Path) -> None:
    (scenario_root / "unlabeled").mkdir()

    result = CliRunner().invoke(app, ["safety-benchmark", "--scenario-root", str(scenario_root)])

    assert result.exit_code == 2
    assert "missing meta.json" in result.stderr
