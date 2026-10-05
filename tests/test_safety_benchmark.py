import subprocess
from pathlib import Path

import pytest

import app.graph as graph_module
import app.runner as runner_module
from app.config import settings
from app.schemas import RefusalReason
from app.safety_benchmark import (
    ActualOutcome,
    ExpectedOutcome,
    SafetyScenario,
    SafetyScenarioResult,
    ScenarioClass,
    ScenarioPatchError,
    ScenarioRestoreError,
    ScenarioSandboxError,
    applied_scenario_patch,
    assert_scenarios_writable,
    build_report,
    discover_safety_scenarios,
    execute_prepared_scenario,
    execute_safety_scenario,
    run_safety_benchmark,
)


def _scenario(
    name: str,
    scenario_class: ScenarioClass,
    expected: ExpectedOutcome,
    *,
    runnable: bool = True,
) -> SafetyScenario:
    return SafetyScenario.model_validate(
        {
            "name": name,
            "class": scenario_class,
            "expected_outcome": expected,
            "failing_selector": "#submit",
            "rationale": "A labeled scenario.",
            "test_path": Path("spec.ts"),
            "diff_path": Path("change.patch"),
            "runnable": runnable,
        }
    )


def _result(
    name: str,
    scenario_class: ScenarioClass,
    expected: ExpectedOutcome,
    actual: ActualOutcome,
    *,
    latency: float = 1,
    attempts: int | None = None,
    cost: float | None = None,
) -> SafetyScenarioResult:
    return SafetyScenarioResult(
        name=name,
        scenario_class=scenario_class,
        expected_outcome=expected,
        actual_outcome=actual,
        latency_seconds=latency,
        attempts=attempts,
        model_cost_usd=cost,
    )


def test_metrics_keep_errors_separate_from_refusals() -> None:
    scenarios = (
        _scenario("regression", ScenarioClass.PRODUCT_REGRESSION, ExpectedOutcome.REFUSE),
        _scenario("drift", ScenarioClass.SELECTOR_DRIFT, ExpectedOutcome.REPAIR),
        _scenario("ambiguous", ScenarioClass.AMBIGUOUS, ExpectedOutcome.REFUSE),
    )
    outcomes = {
        "regression": ActualOutcome.REPAIR,
        "drift": ActualOutcome.REFUSE,
        "ambiguous": ActualOutcome.ERROR,
    }

    def execute(scenario: SafetyScenario) -> SafetyScenarioResult:
        return _result(
            scenario.name,
            scenario.scenario_class,
            scenario.expected_outcome,
            outcomes[scenario.name],
        )

    report = run_safety_benchmark(reversed(scenarios), execute)
    assert [result.name for result in report.results] == ["ambiguous", "drift", "regression"]
    assert report.metrics.false_green_rate == 1.0
    assert report.metrics.repair_precision == 0.0
    assert report.metrics.correct_refusal_rate == 0.0
    assert report.metrics.incorrect_refusal_rate == 1.0
    assert report.metrics.error_count == 1


def test_discovery_rejects_ambiguous_test_inputs(tmp_path: Path) -> None:
    directory = tmp_path / "scenario"
    directory.mkdir()
    (directory / "meta.json").write_text(
        '{"class":"selector_drift","expected_outcome":"repair","failing_selector":"#x","rationale":"ok"}'
    )
    (directory / "change.patch").write_text("")
    (directory / "a.ts").write_text("")
    (directory / "b.ts").write_text("")
    with pytest.raises(ValueError, match="exactly one test file"):
        discover_safety_scenarios(tmp_path)


def test_checked_in_scenarios_are_labeled() -> None:
    scenarios = discover_safety_scenarios(Path("examples/scenarios"))

    assert [scenario.name for scenario in scenarios] == [
        "classname-rename",
        "id-rename",
        "jsx-context",
        "product-regression",
    ]
    assert scenarios[-1].expected_outcome is ExpectedOutcome.REFUSE


def test_static_fixture_is_the_only_checked_in_scenario_that_is_not_runnable() -> None:
    # jsx-context is a token-benchmark fixture, not a Playwright test. If it were scored it
    # would count as a failed repair and skew every rate.
    runnable = {s.name: s.runnable for s in discover_safety_scenarios(Path("examples/scenarios"))}

    assert runnable == {
        "classname-rename": True,
        "id-rename": True,
        "jsx-context": False,
        "product-regression": True,
    }


def test_every_runnable_checked_in_scenario_matches_the_demo_app_in_some_state() -> None:
    # Guards the corpus itself: a patch that neither applies nor is already applied (as
    # classname-rename's once appeared to) would make a CI run report a permanent error.
    root = Path("examples/scenarios")
    for scenario in discover_safety_scenarios(root):
        if not scenario.runnable:
            continue
        patch = str(scenario.diff_path.resolve())
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        forward = subprocess.run(
            ["git", "apply", "--check", patch], cwd=toplevel, capture_output=True, text=True
        )
        reverse = subprocess.run(
            ["git", "apply", "--check", "--reverse", patch],
            cwd=toplevel,
            capture_output=True,
            text=True,
        )
        assert forward.returncode == 0 or reverse.returncode == 0, (
            f"{scenario.name}: change.patch matches the demo app in neither state: "
            f"{forward.stderr.strip()}"
        )


def _scenario_at(test_path: Path, *, runnable: bool = True) -> SafetyScenario:
    return SafetyScenario.model_validate(
        {
            "name": "s",
            "class": ScenarioClass.SELECTOR_DRIFT,
            "expected_outcome": ExpectedOutcome.REPAIR,
            "failing_selector": "#x",
            "rationale": "A labeled scenario.",
            "test_path": test_path,
            "diff_path": test_path.parent / "change.patch",
            "runnable": runnable,
        }
    )


def test_a_scenario_file_the_sandbox_forbids_writing_fails_fast_with_guidance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "sandbox_mode", "relaxed")
    monkeypatch.setattr(settings, "write_globs", "*.spec.ts,**/*.spec.ts")

    with pytest.raises(ScenarioSandboxError, match="E2E_HEALER_WRITE_GLOBS") as caught:
        # A file literally named spec.ts does not match `*.spec.ts`.
        assert_scenarios_writable([_scenario_at(tmp_path / "spec.ts")])

    assert "s: " in str(caught.value)


def test_scenario_files_the_sandbox_allows_pass_the_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "sandbox_mode", "relaxed")
    monkeypatch.setattr(settings, "write_globs", "*.spec.ts,**/*.spec.ts,spec.ts,**/spec.ts")

    assert_scenarios_writable(
        [_scenario_at(tmp_path / "spec.ts"), _scenario_at(tmp_path / "login.spec.ts")]
    )


def test_the_preflight_ignores_scenarios_that_are_not_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A static fixture is never edited, so its filename must not matter.
    monkeypatch.setattr(settings, "sandbox_mode", "relaxed")
    monkeypatch.setattr(settings, "write_globs", "*.spec.ts,**/*.spec.ts")

    assert_scenarios_writable([_scenario_at(tmp_path / "fixture.tsx", runnable=False)])


def test_runnable_defaults_to_true_and_is_read_from_metadata(tmp_path: Path) -> None:
    for name, extra in (("default", ""), ("static", ',"runnable":false')):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "meta.json").write_text(
            '{"class":"selector_drift","expected_outcome":"repair",'
            f'"failing_selector":"#x","rationale":"ok"{extra}}}'
        )
        (directory / "change.patch").write_text("")
        (directory / "spec.ts").write_text("")

    by_name = {s.name: s.runnable for s in discover_safety_scenarios(tmp_path)}

    assert by_name == {"default": True, "static": False}


def test_skipped_scenarios_are_reported_but_never_scored_or_executed() -> None:
    scenarios = (
        _scenario("static", ScenarioClass.SELECTOR_DRIFT, ExpectedOutcome.REPAIR, runnable=False),
        _scenario("drift", ScenarioClass.SELECTOR_DRIFT, ExpectedOutcome.REPAIR),
    )
    executed: list[str] = []

    def execute(scenario: SafetyScenario) -> SafetyScenarioResult:
        executed.append(scenario.name)
        return _result(
            scenario.name, scenario.scenario_class, scenario.expected_outcome, ActualOutcome.REPAIR
        )

    report = run_safety_benchmark(scenarios, execute)

    assert executed == ["drift"]
    assert {r.name: r.actual_outcome for r in report.results} == {
        "drift": ActualOutcome.REPAIR,
        "static": ActualOutcome.SKIPPED,
    }
    # The skipped scenario is in no population: it is neither a wrong refusal nor an error.
    assert report.metrics.incorrect_refusal_rate == 0.0
    assert report.metrics.sample_sizes.incorrect_refusal_rate == 1
    assert report.metrics.error_count == 0
    drift = next(s for s in report.per_class if s.scenario_class is ScenarioClass.SELECTOR_DRIFT)
    assert (drift.scenarios, drift.skipped, drift.correct) == (2, 1, 1)


def test_per_class_summary_lists_every_class_including_empty_ones() -> None:
    report = build_report(
        [
            _result(
                "regression",
                ScenarioClass.PRODUCT_REGRESSION,
                ExpectedOutcome.REFUSE,
                ActualOutcome.REPAIR,
                latency=4,
                attempts=2,
            ),
            _result(
                "drift-a",
                ScenarioClass.SELECTOR_DRIFT,
                ExpectedOutcome.REPAIR,
                ActualOutcome.REPAIR,
                latency=2,
                attempts=1,
            ),
            _result(
                "drift-b",
                ScenarioClass.SELECTOR_DRIFT,
                ExpectedOutcome.REPAIR,
                ActualOutcome.ERROR,
                latency=6,
            ),
        ]
    )

    assert [s.scenario_class for s in report.per_class] == list(ScenarioClass)
    by_class = {s.scenario_class: s for s in report.per_class}
    drift = by_class[ScenarioClass.SELECTOR_DRIFT]
    assert (drift.scenarios, drift.repaired, drift.errors, drift.correct) == (2, 1, 1, 1)
    # Errors count toward latency but not toward attempts, which an error never reports.
    assert drift.mean_latency_seconds == 4.0
    assert drift.mean_attempts == 1.0
    regression = by_class[ScenarioClass.PRODUCT_REGRESSION]
    assert (regression.expected_refuse, regression.repaired, regression.correct) == (1, 1, 0)
    # A class with no scenarios is listed with zeros and no averages, so the gap is visible.
    ambiguous = by_class[ScenarioClass.AMBIGUOUS]
    assert (ambiguous.scenarios, ambiguous.correct) == (0, 0)
    assert ambiguous.mean_latency_seconds is None
    assert ambiguous.mean_attempts is None


def test_metric_sample_sizes_expose_the_denominators() -> None:
    report = build_report(
        [
            _result(
                "regression",
                ScenarioClass.PRODUCT_REGRESSION,
                ExpectedOutcome.REFUSE,
                ActualOutcome.REFUSE,
            ),
            _result(
                "drift-a",
                ScenarioClass.SELECTOR_DRIFT,
                ExpectedOutcome.REPAIR,
                ActualOutcome.REPAIR,
            ),
            _result(
                "drift-b",
                ScenarioClass.SELECTOR_DRIFT,
                ExpectedOutcome.REPAIR,
                ActualOutcome.REPAIR,
            ),
        ]
    )

    sizes = report.metrics.sample_sizes
    assert (sizes.false_green_rate, sizes.repair_precision) == (1, 2)
    assert (sizes.correct_refusal_rate, sizes.incorrect_refusal_rate) == (1, 2)
    assert report.metrics.false_green_rate == 0.0


def test_cost_is_unavailable_unless_every_scored_scenario_reports_it() -> None:
    drift = (ScenarioClass.SELECTOR_DRIFT, ExpectedOutcome.REPAIR, ActualOutcome.REPAIR)

    unmeasured = build_report([_result("a", *drift), _result("b", *drift)])
    partial = build_report([_result("a", *drift, cost=0.01), _result("b", *drift)])
    measured = build_report([_result("a", *drift, cost=0.01), _result("b", *drift, cost=0.02)])

    # None means "not measured", never zero: a missing cost must not read as a free run.
    assert unmeasured.total_model_cost_usd is None
    assert partial.total_model_cost_usd is None
    assert measured.total_model_cost_usd == 0.03


# --- executing one scenario through the graph (graph and Playwright stubbed) ---------


_CHANGE = {"instructions": [{"line": 1}]}
_NO_CHANGE = {"instructions": []}


class _StubGraph:
    def __init__(self, final: dict[str, object], on_invoke=None) -> None:
        self._final = final
        self._on_invoke = on_invoke

    def invoke(self, state: dict[str, object]) -> dict[str, object]:
        if self._on_invoke is not None:
            self._on_invoke(state)
        return {**state, **self._final}


@pytest.fixture
def graph_scenario(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SafetyScenario:
    monkeypatch.setattr(settings, "sandbox_mode", "relaxed")
    monkeypatch.setattr(settings, "write_globs", "*.spec.ts,**/*.spec.ts")
    (tmp_path / "s.spec.ts").write_text("await page.click('#old')\n")
    (tmp_path / "change.patch").write_text("")
    monkeypatch.setattr(
        runner_module, "run_playwright", lambda path: (False, "Error: locator('#old') timed out")
    )
    return _scenario_at(tmp_path / "s.spec.ts")


def test_a_refusal_records_why_the_graph_refused_and_how_many_attempts_it_took(
    monkeypatch: pytest.MonkeyPatch, graph_scenario: SafetyScenario
) -> None:
    final = {
        "is_success": False,
        "refusal_reason": RefusalReason.LOOP_CAP_REACHED,
        "evidence_candidates": [_CHANGE, _CHANGE, _CHANGE],
    }
    monkeypatch.setattr(graph_module, "build_graph", lambda: _StubGraph(final))

    result = execute_safety_scenario(graph_scenario)

    assert result.actual_outcome is ActualOutcome.REFUSE
    assert result.refusal_reason == "loop_cap_reached"
    assert result.attempts == 3


def test_a_candidate_with_no_instructions_is_not_a_repair_attempt(
    monkeypatch: pytest.MonkeyPatch, graph_scenario: SafetyScenario
) -> None:
    # What the checked-in product-regression scenario does: the model diagnoses the failure,
    # proposes no patch, and the loop re-runs the unchanged test until the cap.
    final = {
        "is_success": False,
        "refusal_reason": RefusalReason.LOOP_CAP_REACHED,
        "evidence_candidates": [_NO_CHANGE, _NO_CHANGE, _NO_CHANGE],
    }
    monkeypatch.setattr(graph_module, "build_graph", lambda: _StubGraph(final))

    result = execute_safety_scenario(graph_scenario)

    assert result.actual_outcome is ActualOutcome.REFUSE
    assert result.refusal_reason == "loop_cap_reached"
    assert result.attempts == 0


def test_only_the_candidates_that_proposed_a_change_are_counted(
    monkeypatch: pytest.MonkeyPatch, graph_scenario: SafetyScenario
) -> None:
    final = {
        "is_success": True,
        "evidence_candidates": [_NO_CHANGE, _CHANGE, _NO_CHANGE, _CHANGE],
    }
    monkeypatch.setattr(graph_module, "build_graph", lambda: _StubGraph(final))

    assert execute_safety_scenario(graph_scenario).attempts == 2


def test_a_repair_carries_no_refusal_reason(
    monkeypatch: pytest.MonkeyPatch, graph_scenario: SafetyScenario
) -> None:
    # A reason left over in state from an earlier retry must not be attributed to a repair.
    final = {
        "is_success": True,
        "refusal_reason": RefusalReason.PROVIDER_ERROR,
        "evidence_candidates": [_CHANGE],
    }
    monkeypatch.setattr(graph_module, "build_graph", lambda: _StubGraph(final))

    result = execute_safety_scenario(graph_scenario)

    assert result.actual_outcome is ActualOutcome.REPAIR
    assert result.refusal_reason is None
    assert result.attempts == 1


def test_a_scenario_that_already_passes_is_an_error_and_never_reaches_the_graph(
    monkeypatch: pytest.MonkeyPatch, graph_scenario: SafetyScenario
) -> None:
    monkeypatch.setattr(runner_module, "run_playwright", lambda path: (True, ""))
    monkeypatch.setattr(graph_module, "build_graph", lambda: pytest.fail("the graph must not run"))

    result = execute_safety_scenario(graph_scenario)

    assert result.actual_outcome is ActualOutcome.ERROR
    assert result.error is not None
    assert "passed before healing" in result.error


def test_the_scenario_test_file_is_restored_after_the_graph_edits_it(
    monkeypatch: pytest.MonkeyPatch, graph_scenario: SafetyScenario
) -> None:
    original = graph_scenario.test_path.read_text()

    def edit(state: dict[str, object]) -> None:
        graph_scenario.test_path.write_text("await page.click('#new')\n")

    final = {"is_success": True, "evidence_candidates": [{}]}
    monkeypatch.setattr(graph_module, "build_graph", lambda: _StubGraph(final, on_invoke=edit))

    execute_safety_scenario(graph_scenario)

    assert graph_scenario.test_path.read_text() == original


# --- scenario preparation against a real git repository -----------------------------

_PATCH = """diff --git a/app.txt b/app.txt
--- a/app.txt
+++ b/app.txt
@@ -1 +1 @@
-old
+new
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo_scenario(tmp_path: Path) -> SafetyScenario:
    """A throwaway git repository whose single scenario patch changes ``app.txt``."""
    _git(tmp_path, "init", "-q")
    (tmp_path / "app.txt").write_text("old\n")
    directory = tmp_path / "scenarios" / "s1"
    directory.mkdir(parents=True)
    (directory / "spec.ts").write_text("")
    (directory / "change.patch").write_text(_PATCH)
    return SafetyScenario.model_validate(
        {
            "name": "s1",
            "class": ScenarioClass.SELECTOR_DRIFT,
            "expected_outcome": ExpectedOutcome.REPAIR,
            "failing_selector": "#x",
            "rationale": "A labeled scenario.",
            "test_path": directory / "spec.ts",
            "diff_path": directory / "change.patch",
        }
    )


def test_patch_is_applied_inside_the_context_and_restored_after(
    repo_scenario: SafetyScenario, tmp_path: Path
) -> None:
    with applied_scenario_patch(repo_scenario):
        assert (tmp_path / "app.txt").read_text() == "new\n"

    assert (tmp_path / "app.txt").read_text() == "old\n"


def test_patch_is_restored_even_when_the_scenario_raises(
    repo_scenario: SafetyScenario, tmp_path: Path
) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with applied_scenario_patch(repo_scenario):
            raise RuntimeError("boom")

    assert (tmp_path / "app.txt").read_text() == "old\n"


def test_a_change_that_is_already_present_runs_as_is_and_is_left_untouched(
    repo_scenario: SafetyScenario, tmp_path: Path
) -> None:
    # Some scenarios ship the app pre-broken and keep the patch as a reference diff.
    (tmp_path / "app.txt").write_text("new\n")
    seen: list[str] = []

    with applied_scenario_patch(repo_scenario):
        seen.append((tmp_path / "app.txt").read_text())

    assert seen == ["new\n"]
    # It must not be reversed: the app is left exactly as it was found.
    assert (tmp_path / "app.txt").read_text() == "new\n"


def test_an_app_that_matches_neither_state_fails_loudly(
    repo_scenario: SafetyScenario, tmp_path: Path
) -> None:
    (tmp_path / "app.txt").write_text("drifted\n")

    with pytest.raises(ScenarioPatchError, match="neither applies cleanly nor is already"):
        with applied_scenario_patch(repo_scenario):
            pytest.fail("the scenario body must not run on an app that does not match")

    assert (tmp_path / "app.txt").read_text() == "drifted\n"


def test_prepared_execution_runs_against_the_broken_tree_and_restores_it(
    repo_scenario: SafetyScenario, tmp_path: Path
) -> None:
    seen: list[str] = []

    def execute(scenario: SafetyScenario) -> SafetyScenarioResult:
        seen.append((tmp_path / "app.txt").read_text())
        return _result(
            scenario.name, scenario.scenario_class, scenario.expected_outcome, ActualOutcome.REPAIR
        )

    result = execute_prepared_scenario(repo_scenario, execute)

    assert seen == ["new\n"]
    assert result.actual_outcome is ActualOutcome.REPAIR
    assert (tmp_path / "app.txt").read_text() == "old\n"


def test_a_patch_that_cannot_apply_becomes_an_error_result_not_a_crash(
    repo_scenario: SafetyScenario, tmp_path: Path
) -> None:
    (tmp_path / "app.txt").write_text("drifted\n")

    result = execute_prepared_scenario(
        repo_scenario, lambda scenario: pytest.fail("must not execute")
    )

    assert result.actual_outcome is ActualOutcome.ERROR
    assert result.error is not None
    assert "neither applies cleanly nor is already" in result.error


def test_a_failed_restore_aborts_the_run_instead_of_continuing_on_a_modified_tree(
    repo_scenario: SafetyScenario, tmp_path: Path
) -> None:
    def corrupt(scenario: SafetyScenario) -> SafetyScenarioResult:
        # The scenario run leaves the app in a state the patch cannot be reversed from.
        (tmp_path / "app.txt").write_text("something else\n")
        return _result(
            scenario.name, scenario.scenario_class, scenario.expected_outcome, ActualOutcome.REPAIR
        )

    with pytest.raises(ScenarioRestoreError, match="could not reverse"):
        run_safety_benchmark(
            [repo_scenario], lambda scenario: execute_prepared_scenario(scenario, corrupt)
        )
