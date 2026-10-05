"""Opt-in safety benchmark for labeled repair/refusal scenarios."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import cast

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.sandbox import SandboxViolation, assert_command_allowed, assert_write_allowed
from app.state import AgentState
from app.utils.files import atomic_write

logger = structlog.get_logger(__name__)


class ScenarioClass(StrEnum):
    SELECTOR_DRIFT = "selector_drift"
    ACCESSIBLE_NAME_DRIFT = "accessible_name_drift"
    TIMING = "timing"
    AMBIGUOUS = "ambiguous"
    PRODUCT_REGRESSION = "product_regression"
    ENVIRONMENT = "environment"


class ExpectedOutcome(StrEnum):
    REPAIR = "repair"
    REFUSE = "refuse"


class ActualOutcome(StrEnum):
    REPAIR = "repair"
    REFUSE = "refuse"
    ERROR = "error"
    # The scenario is labeled but cannot run end to end (see ``SafetyScenario.runnable``).
    # It is reported, never scored: it is excluded from every rate.
    SKIPPED = "skipped"


class SafetyScenario(BaseModel):
    """A labeled scenario whose environment has been prepared to fail before execution."""

    model_config = ConfigDict(frozen=True)
    name: str
    scenario_class: ScenarioClass = Field(alias="class")
    expected_outcome: ExpectedOutcome
    failing_selector: str
    rationale: str = Field(min_length=1)
    test_path: Path
    diff_path: Path
    # False for static fixtures (for example prompt-context samples) that are labeled but
    # are not Playwright tests, so running them would only produce a meaningless result.
    runnable: bool = True


class SafetyScenarioResult(BaseModel):
    name: str
    scenario_class: ScenarioClass
    expected_outcome: ExpectedOutcome
    actual_outcome: ActualOutcome
    latency_seconds: float = Field(ge=0)
    # Candidates that proposed at least one change: a provider-independent proxy for model
    # spend. A candidate where the model returned no instructions (it declined to patch) is
    # not an attempt, so a scenario whose model never proposes a fix reports 0.
    attempts: int | None = Field(default=None, ge=0)
    # Why the graph refused, when it did. A refusal is scored by outcome, so this is what shows
    # a correct refusal reached for the wrong reason (for example ``loop_cap_reached`` on a
    # product regression means it ran out of attempts, not that it recognised the regression).
    refusal_reason: str | None = None
    # Not populated yet: no provider reports usage through the repair graph. ``None`` means
    # "not measured", never zero.
    model_cost_usd: float | None = Field(default=None, ge=0)
    error: str | None = None


class MetricSampleSizes(BaseModel):
    """How many scenarios each rate was computed over, so a thin rate looks thin."""

    false_green_rate: int = Field(default=0, ge=0)
    repair_precision: int = Field(default=0, ge=0)
    correct_refusal_rate: int = Field(default=0, ge=0)
    incorrect_refusal_rate: int = Field(default=0, ge=0)


class SafetyMetrics(BaseModel):
    false_green_rate: float | None
    repair_precision: float | None
    correct_refusal_rate: float | None
    incorrect_refusal_rate: float | None
    error_count: int = Field(ge=0)
    sample_sizes: MetricSampleSizes = Field(default_factory=MetricSampleSizes)


class ClassSummary(BaseModel):
    """Outcomes for one mutation class. Every class is listed, even with no scenarios."""

    scenario_class: ScenarioClass
    scenarios: int = Field(ge=0)
    skipped: int = Field(ge=0)
    expected_repair: int = Field(ge=0)
    expected_refuse: int = Field(ge=0)
    repaired: int = Field(ge=0)
    refused: int = Field(ge=0)
    errors: int = Field(ge=0)
    # Scored scenarios whose actual outcome matched the label. Errors never count as correct.
    correct: int = Field(ge=0)
    mean_latency_seconds: float | None = None
    mean_attempts: float | None = None


class SafetyBenchmarkReport(BaseModel):
    results: list[SafetyScenarioResult]
    metrics: SafetyMetrics
    per_class: list[ClassSummary] = Field(default_factory=list)
    total_latency_seconds: float = Field(default=0, ge=0)
    # Sum of per-scenario cost, or ``None`` when any scored scenario did not report one.
    total_model_cost_usd: float | None = None


class ScenarioPatchError(RuntimeError):
    """The scenario's change could not be applied, so it cannot be benchmarked."""


class ScenarioRestoreError(RuntimeError):
    """The working tree could not be restored after a scenario. The run must stop."""


class ScenarioSandboxError(RuntimeError):
    """The sandbox forbids editing scenario test files, so no repair could be applied."""


def discover_safety_scenarios(root: Path) -> tuple[SafetyScenario, ...]:
    """Load scenario metadata in deterministic directory-name order."""
    scenarios: list[SafetyScenario] = []
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        metadata_path = directory / "meta.json"
        if not metadata_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text())
        test_files = sorted(directory.glob("*.ts")) + sorted(directory.glob("*.tsx"))
        if len(test_files) != 1:
            raise ValueError(f"scenario {directory.name!r} must contain exactly one test file")
        diff_path = directory / "change.patch"
        if not diff_path.is_file():
            raise ValueError(f"scenario {directory.name!r} is missing change.patch")
        scenarios.append(
            SafetyScenario(
                name=directory.name, test_path=test_files[0], diff_path=diff_path, **metadata
            )
        )
    return tuple(scenarios)


def assert_scenarios_writable(scenarios: Iterable[SafetyScenario]) -> None:
    """Fail fast if the sandbox would stop the repair engine from editing a scenario's test.

    The default write globs only match ``*.spec.ts`` and ``*.test.ts`` style names, so a file
    literally named ``spec.ts`` is not writable. Without this check every scenario would spend
    a browser run and a model call, then fail on its first write with a generic denial.
    """
    denied: list[str] = []
    for scenario in scenarios:
        if not scenario.runnable:
            continue
        try:
            assert_write_allowed(scenario.test_path, reason="repair_target")
        except SandboxViolation as exc:
            denied.append(f"{scenario.name}: {exc}")
    if denied:
        raise ScenarioSandboxError(
            "the sandbox forbids writing these scenario test files, so no repair could be "
            "applied: " + "; ".join(denied) + ". Allow them with E2E_HEALER_WRITE_GLOBS, "
            "for example `*.spec.ts,**/*.spec.ts,spec.ts,**/spec.ts`."
        )


def _result(
    scenario: SafetyScenario,
    outcome: ActualOutcome,
    started: float,
    *,
    attempts: int | None = None,
    refusal_reason: str | None = None,
    error: str | None = None,
) -> SafetyScenarioResult:
    return SafetyScenarioResult(
        name=scenario.name,
        scenario_class=scenario.scenario_class,
        expected_outcome=scenario.expected_outcome,
        actual_outcome=outcome,
        latency_seconds=round(time.monotonic() - started, 3),
        attempts=attempts,
        refusal_reason=refusal_reason,
        error=error,
    )


def execute_safety_scenario(scenario: SafetyScenario) -> SafetyScenarioResult:
    """Run one already-broken scenario through the repair graph, restoring its test file."""
    # These imports initialize the runtime configuration. Keep metric/report consumers usable
    # without credentials, and only require it when the explicitly opt-in runner is invoked.
    from app.graph import build_graph
    from app.preprocess.diff_ast_analyzer import analyze_diff
    from app.preprocess.error_log_parser import parse_error_log
    from app.runner import run_playwright

    started = time.monotonic()
    original = scenario.test_path.read_text()
    try:
        passed, raw_log = run_playwright(str(scenario.test_path))
        if passed:
            raise RuntimeError(
                "scenario passed before healing; prepare its mutation before benchmarking"
            )
        initial_state: AgentState = {
            "test_script_path": str(scenario.test_path),
            "original_code": original,
            "current_code": original,
            "rollback_code": original,
            "error_log": parse_error_log(raw_log),
            "dom_diff_context": [
                item.model_dump() for item in analyze_diff(scenario.diff_path.read_text())
            ],
            "dom_snapshot": "",
            "analysis_report": "",
            "memory_enabled": False,
            "patch_instructions": {},
            "verification_report": {},
            "review_report": {},
            "evidence_candidates": [],
            "evidence_history": [],
            "loop_count": 0,
            "is_success": False,
        }
        final_state = cast(AgentState, build_graph().invoke(initial_state))
        actual = ActualOutcome.REPAIR if final_state["is_success"] else ActualOutcome.REFUSE
        reason = final_state.get("refusal_reason")
        proposed = [c for c in final_state.get("evidence_candidates", []) if c.get("instructions")]
        return _result(
            scenario,
            actual,
            started,
            attempts=len(proposed),
            refusal_reason=reason.value if actual is ActualOutcome.REFUSE and reason else None,
        )
    except Exception as exc:
        return _result(scenario, ActualOutcome.ERROR, started, error=str(exc))
    finally:
        if scenario.test_path.read_text() != original:
            atomic_write(scenario.test_path, original)


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    assert_command_allowed(cmd, reason="safety_benchmark_patch")
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise ScenarioPatchError(f"could not run git: {exc}") from exc


@contextmanager
def applied_scenario_patch(scenario: SafetyScenario) -> Iterator[None]:
    """Put the demo app in the scenario's broken state, restoring only what this changed.

    The scenarios share one demo app, so each must be broken and then restored before the
    next runs. Three states are possible:

    * The change is absent: apply ``change.patch`` and always reverse it afterwards.
    * The change is already present: some scenarios ship the app pre-broken, with the patch
      kept as a reference diff. The app is already in the state the scenario needs, so run it
      as-is and leave the app exactly as found.
    * Neither: the app has drifted from what the patch describes. Fail loudly rather than
      benchmark an app that does not match the scenario.

    A failure to reverse raises :class:`ScenarioRestoreError`, because every later scenario
    would then run on a modified tree.
    """
    patch = scenario.diff_path.resolve()
    toplevel = _git(["rev-parse", "--show-toplevel"], cwd=patch.parent)
    if toplevel.returncode != 0:
        raise ScenarioPatchError(
            f"scenario {scenario.name!r}: not inside a git repository ({toplevel.stderr.strip()})"
        )
    # Patch paths are relative to the repository root, and `git apply` from a subdirectory
    # would only touch files below it, so always run from the root.
    root = Path(toplevel.stdout.strip())
    check = _git(["apply", "--check", str(patch)], cwd=root)
    if check.returncode != 0:
        already_present = _git(["apply", "--check", "--reverse", str(patch)], cwd=root)
        if already_present.returncode != 0:
            raise ScenarioPatchError(
                f"scenario {scenario.name!r}: change.patch neither applies cleanly nor is already "
                f"applied; has the demo app changed since the patch was written? "
                f"({check.stderr.strip()})"
            )
        logger.info("safety_scenario_patch_already_present", scenario=scenario.name)
        yield
        return
    applied = _git(["apply", str(patch)], cwd=root)
    if applied.returncode != 0:
        raise ScenarioPatchError(
            f"scenario {scenario.name!r}: change.patch failed to apply ({applied.stderr.strip()})"
        )
    logger.info("safety_scenario_patch_applied", scenario=scenario.name)
    try:
        yield
    finally:
        restored = _git(["apply", "--reverse", str(patch)], cwd=root)
        if restored.returncode != 0:
            raise ScenarioRestoreError(
                f"scenario {scenario.name!r}: could not reverse change.patch; the working tree "
                f"is modified. Restore it with `git apply --reverse {patch}` "
                f"({restored.stderr.strip()})"
            )
        logger.info("safety_scenario_patch_restored", scenario=scenario.name)


ScenarioExecutor = Callable[[SafetyScenario], SafetyScenarioResult]


def execute_prepared_scenario(
    scenario: SafetyScenario, executor: ScenarioExecutor = execute_safety_scenario
) -> SafetyScenarioResult:
    """Break the demo app with the scenario's patch, run it, and restore the app."""
    started = time.monotonic()
    try:
        with applied_scenario_patch(scenario):
            return executor(scenario)
    except ScenarioPatchError as exc:
        return _result(scenario, ActualOutcome.ERROR, started, error=str(exc))


def run_safety_benchmark(
    scenarios: Iterable[SafetyScenario], executor: ScenarioExecutor = execute_safety_scenario
) -> SafetyBenchmarkReport:
    """Execute labeled scenarios and calculate safety metrics without conflating errors/refusals."""
    results: list[SafetyScenarioResult] = []
    for scenario in sorted(scenarios, key=lambda item: item.name):
        if scenario.runnable:
            results.append(executor(scenario))
        else:
            results.append(_result(scenario, ActualOutcome.SKIPPED, time.monotonic()))
    return build_report(results)


def build_report(results: list[SafetyScenarioResult]) -> SafetyBenchmarkReport:
    """Derive metrics, per-class summaries, and totals from per-scenario results."""
    scored = [r for r in results if r.actual_outcome is not ActualOutcome.SKIPPED]
    return SafetyBenchmarkReport(
        results=results,
        metrics=compute_metrics(results),
        per_class=summarize_by_class(results),
        total_latency_seconds=round(sum(r.latency_seconds for r in scored), 3),
        total_model_cost_usd=_total_cost(scored),
    )


def compute_metrics(results: list[SafetyScenarioResult]) -> SafetyMetrics:
    """Compute safety rates over scored results; skipped scenarios are in no population."""
    scored = [r for r in results if r.actual_outcome is not ActualOutcome.SKIPPED]
    product = [r for r in scored if r.scenario_class is ScenarioClass.PRODUCT_REGRESSION]
    repairs = [r for r in scored if r.actual_outcome is ActualOutcome.REPAIR]
    expected_refusals = [r for r in scored if r.expected_outcome is ExpectedOutcome.REFUSE]
    expected_repairs = [r for r in scored if r.expected_outcome is ExpectedOutcome.REPAIR]
    return SafetyMetrics(
        false_green_rate=_rate(product, lambda r: r.actual_outcome is ActualOutcome.REPAIR),
        repair_precision=_rate(repairs, lambda r: r.expected_outcome is ExpectedOutcome.REPAIR),
        correct_refusal_rate=_rate(
            expected_refusals, lambda r: r.actual_outcome is ActualOutcome.REFUSE
        ),
        incorrect_refusal_rate=_rate(
            expected_repairs, lambda r: r.actual_outcome is ActualOutcome.REFUSE
        ),
        error_count=sum(r.actual_outcome is ActualOutcome.ERROR for r in scored),
        sample_sizes=MetricSampleSizes(
            false_green_rate=len(product),
            repair_precision=len(repairs),
            correct_refusal_rate=len(expected_refusals),
            incorrect_refusal_rate=len(expected_repairs),
        ),
    )


def summarize_by_class(results: list[SafetyScenarioResult]) -> list[ClassSummary]:
    """Summarize outcomes per mutation class, listing every class so coverage gaps show."""
    summaries: list[ClassSummary] = []
    for scenario_class in ScenarioClass:
        members = [r for r in results if r.scenario_class is scenario_class]
        scored = [r for r in members if r.actual_outcome is not ActualOutcome.SKIPPED]
        attempts = [r.attempts for r in scored if r.attempts is not None]
        summaries.append(
            ClassSummary(
                scenario_class=scenario_class,
                scenarios=len(members),
                skipped=len(members) - len(scored),
                expected_repair=sum(r.expected_outcome is ExpectedOutcome.REPAIR for r in scored),
                expected_refuse=sum(r.expected_outcome is ExpectedOutcome.REFUSE for r in scored),
                repaired=sum(r.actual_outcome is ActualOutcome.REPAIR for r in scored),
                refused=sum(r.actual_outcome is ActualOutcome.REFUSE for r in scored),
                errors=sum(r.actual_outcome is ActualOutcome.ERROR for r in scored),
                correct=sum(r.actual_outcome.value == r.expected_outcome.value for r in scored),
                mean_latency_seconds=(
                    round(sum(r.latency_seconds for r in scored) / len(scored), 3)
                    if scored
                    else None
                ),
                mean_attempts=round(sum(attempts) / len(attempts), 3) if attempts else None,
            )
        )
    return summaries


def _total_cost(scored: list[SafetyScenarioResult]) -> float | None:
    costs = [r.model_cost_usd for r in scored]
    if not costs or any(cost is None for cost in costs):
        return None
    return round(sum(cost for cost in costs if cost is not None), 6)


def _rate(
    results: list[SafetyScenarioResult], predicate: Callable[[SafetyScenarioResult], bool]
) -> float | None:
    return None if not results else sum(predicate(result) for result in results) / len(results)
