"""Build demo-page/src/data/demo.json from the scenario corpus.

Everything written here is real and language-neutral: each scenario's spec.ts, change.patch and
meta.json, the Playwright failure logs in ``scripts/logs/`` (captured against the demo app with
each patch applied), and the actual output of the Data Preprocessor. The simulated engine steps
and all human-readable text live in ``src/runs.ts`` and ``src/i18n/``.

Run from the repository root:

    E2E_HEALER_LLM_MODEL=x uv run python demo-page/scripts/build_data.py
"""

import json
from pathlib import Path

from app.preprocess.diff_ast_analyzer import analyze_diff
from app.preprocess.error_log_parser import parse_error_log

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LOGS = HERE / "logs"
OUT = HERE.parent / "src" / "data" / "demo.json"
SCENARIOS = REPO / "examples" / "scenarios"


def headline(log: str) -> str:
    """The headline lines of a Playwright failure, up to its error-context pointer."""
    keep: list[str] = []
    for line in log.splitlines():
        text = line.strip()
        if "Error Context" in text:
            break
        if text.startswith(("TimeoutError", "Error:", "- ", "Expected", "2 ×")):
            keep.append(text)
    return "\n".join(keep[:7])


def patch_hunks(patch: str) -> str:
    return "\n".join(
        line
        for line in patch.splitlines()
        if not line.startswith(("diff --git", "index ", "--- ", "+++ "))
    )


def patch_target(patch: str) -> str:
    return next(line[len("+++ b/") :] for line in patch.splitlines() if line.startswith("+++ b/"))


def scenario(directory: Path) -> dict:
    meta = json.loads((directory / "meta.json").read_text())
    patch = (directory / "change.patch").read_text()
    log = (LOGS / f"pw-{directory.name}.log").read_text()
    return {
        "name": directory.name,
        "class": meta["class"],
        "expected": meta["expected_outcome"],
        "failing": meta["failing_selector"],
        "spec": (directory / "spec.ts").read_text().rstrip(),
        "patch": patch_hunks(patch),
        "patchFile": patch_target(patch),
        "failure": headline(log),
        "pre": {
            "error": parse_error_log(log),
            "dom": [change.model_dump() for change in analyze_diff(patch)],
        },
    }


def main() -> None:
    runnable = [
        d
        for d in sorted(SCENARIOS.iterdir())
        if d.is_dir() and json.loads((d / "meta.json").read_text()).get("runnable", True)
    ]
    scenarios = {d.name: scenario(d) for d in runnable}
    OUT.write_text(json.dumps(scenarios, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}: {len(scenarios)} scenarios")


main()
