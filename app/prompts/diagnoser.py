"""System prompt for the Diagnoser node."""

import json

from app.preprocess.jsx_chunker import CodeChunk

SYSTEM_PROMPT = (
    "You are an expert Playwright E2E test debugger. You are given a failure log, the "
    "DOM changes from a git diff (before/after tag + attributes), an optional ARIA page "
    "snapshot captured at failure time, and the current test code. Explain concisely WHY "
    "the test broke: identify which selector/locator failed and, when a DOM attribute change "
    "(id, className, data-testid, role, name) caused it, which one. Use the ARIA snapshot to "
    "correlate the failing selector with what was actually on the page. When a diff check "
    "states that the diff removed no line naming the failing selector, the selector was not "
    "renamed and a different selector is not the fix. An element missing from a failure "
    "snapshot taken when an action timed out may simply render later than the action waited "
    "(behind a loading state or timer), so when the failing call is an action that timed out, "
    "recommend raising that call's timeout first; only a failure after a longer wait shows the "
    "element is no longer rendered because the product's behavior changed. Do not propose a "
    "replacement selector for an element that is merely missing from the snapshot. Output a "
    "short diagnosis only — do NOT write code."
)


def untouched_selector_fact(locator: str) -> str:
    """The prompt line stating that the diff did not rename or remove the failing selector."""
    return (
        f"Diff check: no line removed by the git diff names anything in the failing locator "
        f"{locator}, so the diff did not rename or delete what it matches."
    )


def build_user_prompt(
    error_log: str,
    dom_diff_context: list[dict],
    aria_snapshot: str,
    code_context: CodeChunk,
    untouched_selector: str = "",
) -> str:
    """Build the Diagnoser prompt from the same bounded context used in production."""
    user_prompt = (
        f"Error log:\n{error_log}\n\n"
        f"DOM changes (from git diff):\n{json.dumps(dom_diff_context, indent=2)}\n\n"
    )
    if untouched_selector:
        user_prompt += f"{untouched_selector_fact(untouched_selector)}\n\n"
    if aria_snapshot:
        user_prompt += f"ARIA page snapshot (at failure):\n{aria_snapshot}\n\n"
    context_kind = "whole-file fallback" if code_context.is_fallback else "semantic JSX chunk"
    return (
        user_prompt + f"Current test code context ({context_kind}, lines "
        f"{code_context.start_line}-{code_context.end_line}):\n{code_context.source}"
    )
