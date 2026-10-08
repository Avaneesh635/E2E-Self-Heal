"""Render and compare safety benchmark reports.

The JSON report is the machine-readable artifact (and the committed baseline). This module
turns it into a Markdown summary for humans and computes the change against a baseline run,
so a regression shows up as a trend, not only as a snapshot.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from app.safety_benchmark import (
    GATE_MIN_SAMPLE,
    ActualOutcome,
    ClassSummary,
    GateStatus,
    SafetyBenchmarkReport,
    SafetyScenarioResult,
    compute_metrics,
    evaluate_gates,
    summarize_by_class,
)

_ERROR_PREVIEW_CHARS = 200

_METRIC_LABELS: tuple[tuple[str, str], ...] = (
    ("false_green_rate", "False-green rate (product regressions repaired)"),
    ("repair_precision", "Repair precision (repairs that were expected)"),
    ("correct_refusal_rate", "Correct-refusal rate (expected refusals refused)"),
    ("incorrect_refusal_rate", "Incorrect-refusal rate (expected repairs refused)"),
    ("refusal_accuracy", "Refusal accuracy (correct refusals vs. false heals and false refusals)"),
)


def load_baseline(path: Path) -> SafetyBenchmarkReport | None:
    """Load a previous JSON report, or ``None`` if there is no baseline yet.

    A missing file is the normal state before the first baseline is committed. A file that
    exists but is not a valid report is an error: silently ignoring it would hide that the
    comparison never happened.
    """
    if not path.is_file():
        return None
    try:
        return SafetyBenchmarkReport.model_validate_json(path.read_text())
    except ValidationError as exc:
        # pydantic's full repr is long and links to its docs; the first error is enough here.
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"]) or "report"
        raise ValueError(
            f"baseline {path} is not a valid safety report: {first['msg']} ({where})"
        ) from exc
    except OSError as exc:
        raise ValueError(f"baseline {path} could not be read: {exc}") from exc


def render_markdown(
    report: SafetyBenchmarkReport, baseline: SafetyBenchmarkReport | None = None
) -> str:
    """Render a report, with change columns when a baseline run is provided."""
    lines: list[str] = ["# Safety benchmark", ""]
    lines += [
        "> Informational on pull requests and main. The release gates below block a release "
        "only, and only once a rate is computed over enough scenarios (#292).",
        "",
    ]
    lines += _summary_lines(report, baseline)
    lines += _gate_section(report)
    lines += _metrics_section(report, baseline)
    lines += _class_section(report, baseline)
    lines += _scenario_section(report, baseline)
    lines += _coverage_section(report)
    lines += _error_section(report)
    return "\n".join(lines).rstrip() + "\n"


def _summary_lines(
    report: SafetyBenchmarkReport, baseline: SafetyBenchmarkReport | None
) -> list[str]:
    scored = _scored(report.results)
    skipped = len(report.results) - len(scored)
    latency = f"{report.total_latency_seconds:.1f} s"
    if baseline is not None:
        latency += f" ({_signed(report.total_latency_seconds - baseline.total_latency_seconds)} s)"
    cost = (
        "not measured (no provider usage is captured; compare latency and attempts)"
        if report.total_model_cost_usd is None
        else f"${report.total_model_cost_usd:.4f}"
    )
    attempts = _mean_attempts(report.results)
    attempts_text = "n/a" if attempts is None else f"{attempts:.2f}"
    if baseline is not None:
        base_attempts = _mean_attempts(baseline.results)
        if attempts is not None and base_attempts is not None:
            attempts_text += f" ({_signed(attempts - base_attempts, 2)})"
    baseline_text = (
        "none (first run, or no baseline found)"
        if baseline is None
        else f"{len(baseline.results)} scenarios"
    )
    return [
        f"**{len(scored)} scored, {skipped} skipped, {report.metrics.error_count} errors**",
        "",
        f"- Total latency: {latency}",
        f"- Mean repair attempts per scenario: {attempts_text}",
        f"- Model cost: {cost}",
        f"- Baseline: {baseline_text}",
        "",
    ]


def _gate_section(report: SafetyBenchmarkReport) -> list[str]:
    rows = [
        "| Gate | Threshold | Value | Scenarios (n) | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for gate in report.gates or evaluate_gates(report.metrics):
        value = (
            f"{gate.value:.0f}"
            if gate.name == "error_count" and gate.value is not None
            else _pct(gate.value)
        )
        status = "**FAIL**" if gate.status is GateStatus.FAIL else gate.status.value
        rows.append(
            f"| `{gate.name}` | {gate.threshold} | {value} | {gate.sample_size} | {status} |"
        )
    return [
        "## Release gates",
        "",
        *rows,
        "",
        f"`insufficient_sample` means fewer than {GATE_MIN_SAMPLE} scenarios: reported, not "
        "enforced. A single false green fails its gate at any sample size.",
        "",
    ]


def _metrics_section(
    report: SafetyBenchmarkReport, baseline: SafetyBenchmarkReport | None
) -> list[str]:
    base_metrics = compute_metrics(baseline.results) if baseline is not None else None
    header = "| Metric | Value | Scenarios (n) |"
    divider = "| --- | --- | --- |"
    if base_metrics is not None:
        header += " Change vs baseline |"
        divider += " --- |"
    rows = [header, divider]
    for field, label in _METRIC_LABELS:
        value: float | None = getattr(report.metrics, field)
        count: int = getattr(report.metrics.sample_sizes, field)
        row = f"| {label} | {_pct(value)} | {count} |"
        if base_metrics is not None:
            row += f" {_pct_change(value, getattr(base_metrics, field))} |"
        rows.append(row)
    return ["## Metrics", "", *rows, ""]


def _class_section(
    report: SafetyBenchmarkReport, baseline: SafetyBenchmarkReport | None
) -> list[str]:
    summaries = report.per_class or summarize_by_class(report.results)
    base_by_class = (
        {s.scenario_class: s for s in summarize_by_class(baseline.results)}
        if baseline is not None
        else {}
    )
    header = (
        "| Class | Scenarios | Expected repair / refuse | Repaired | Refused | Errors "
        "| Correct | Mean latency | Mean attempts |"
    )
    divider = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    rows = [header, divider]
    for summary in summaries:
        rows.append(_class_row(summary, base_by_class.get(summary.scenario_class)))
    return ["## By class", "", *rows, ""]


def _class_row(summary: ClassSummary, base: ClassSummary | None) -> str:
    scored = summary.scenarios - summary.skipped
    correct = "—" if scored == 0 else f"{summary.correct}/{scored}"
    if base is not None and scored:
        base_scored = base.scenarios - base.skipped
        if base_scored and (base.correct, base_scored) != (summary.correct, scored):
            correct += f" (was {base.correct}/{base_scored})"
    latency = "—" if summary.mean_latency_seconds is None else f"{summary.mean_latency_seconds} s"
    attempts = "—" if summary.mean_attempts is None else f"{summary.mean_attempts}"
    skipped = f" (+{summary.skipped} skipped)" if summary.skipped else ""
    return (
        f"| `{summary.scenario_class.value}` | {scored}{skipped} "
        f"| {summary.expected_repair} / {summary.expected_refuse} "
        f"| {summary.repaired} | {summary.refused} | {summary.errors} "
        f"| {correct} | {latency} | {attempts} |"
    )


def _scenario_section(
    report: SafetyBenchmarkReport, baseline: SafetyBenchmarkReport | None
) -> list[str]:
    base_by_name = {r.name: r for r in baseline.results} if baseline is not None else {}
    header = (
        "| Scenario | Class | Expected | Actual | Refusal reason | Latency | Attempts | Declined |"
    )
    divider = "| --- | --- | --- | --- | --- | --- | --- | --- |"
    if baseline is not None:
        header += " vs baseline |"
        divider += " --- |"
    rows = [header, divider]
    for result in report.results:
        attempts = "—" if result.attempts is None else str(result.attempts)
        declined = "—" if result.declined is None else str(result.declined)
        reason = "—" if result.refusal_reason is None else f"`{result.refusal_reason}`"
        row = (
            f"| {result.name} | `{result.scenario_class.value}` | {result.expected_outcome.value} "
            f"| {result.actual_outcome.value} | {reason} | {result.latency_seconds:.1f} s "
            f"| {attempts} | {declined} |"
        )
        if baseline is not None:
            row += f" {_outcome_change(result, base_by_name.get(result.name))} |"
        rows.append(row)
    lines = ["## Scenarios", "", *rows, ""]
    if baseline is not None:
        current = {r.name for r in report.results}
        removed = sorted(name for name in base_by_name if name not in current)
        if removed:
            lines += [f"Removed since baseline: {', '.join(removed)}", ""]
    return lines


def _coverage_section(report: SafetyBenchmarkReport) -> list[str]:
    summaries = report.per_class or summarize_by_class(report.results)
    empty = [s.scenario_class.value for s in summaries if s.scenarios - s.skipped == 0]
    if not empty:
        return []
    return [
        "## Coverage gaps",
        "",
        "No scored scenarios exist for: " + ", ".join(f"`{name}`" for name in empty) + ". "
        "Any number above says nothing about these classes.",
        "",
    ]


def _error_section(report: SafetyBenchmarkReport) -> list[str]:
    failed = [r for r in report.results if r.actual_outcome is ActualOutcome.ERROR]
    if not failed:
        return []
    lines = ["## Errors", ""]
    for result in failed:
        message = " ".join((result.error or "no message").split())
        if len(message) > _ERROR_PREVIEW_CHARS:
            message = message[:_ERROR_PREVIEW_CHARS] + "…"
        lines.append(f"- `{result.name}`: {message}")
    return [*lines, ""]


def _scored(results: list[SafetyScenarioResult]) -> list[SafetyScenarioResult]:
    return [r for r in results if r.actual_outcome is not ActualOutcome.SKIPPED]


def _mean_attempts(results: list[SafetyScenarioResult]) -> float | None:
    attempts = [r.attempts for r in _scored(results) if r.attempts is not None]
    return sum(attempts) / len(attempts) if attempts else None


def _outcome_change(current: SafetyScenarioResult, base: SafetyScenarioResult | None) -> str:
    if base is None:
        return "new"
    if base.actual_outcome is current.actual_outcome:
        return "unchanged"
    return f"**{base.actual_outcome.value} → {current.actual_outcome.value}**"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _pct_change(value: float | None, base: float | None) -> str:
    if value is None or base is None:
        return "—"
    delta = (value - base) * 100
    return "unchanged" if abs(delta) < 0.05 else f"{delta:+.1f} pp"


def _signed(value: float, digits: int = 1) -> str:
    return f"{value:+.{digits}f}"
