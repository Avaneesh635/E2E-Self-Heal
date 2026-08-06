"""Patch Generator node: produce a narrow, schema-constrained fix."""

import re
from pathlib import Path
from typing import cast

import structlog

from app.llm import generate_patch
from app.prompts.patch_generator import (
    DomDiffEntry,
    build_system_prompt,
    detect_framework,
)
from app.sandbox import SandboxViolation, assert_patch_boundary_allowed
from app.schemas import PatchInstruction
from app.state import AgentState
from app.utils.files import split_line_ending

logger = structlog.get_logger(__name__)
_ALLOWED_PATCH_CALL = re.compile(
    r"(?:\bpage\.|\.)"
    r"(?:locator|getByRole|getByText|getByLabel|getByPlaceholder|getByAltText|"
    r"getByTitle|getByTestId|click|dblclick|fill|type|check|uncheck|selectOption|"
    r"setInputFiles|press|hover|focus|waitFor[A-Za-z]*)\s*\("
)
_ASSERTION_CALL = re.compile(r"(?:\b(?:expect|assert)\s*\(|\.(?:toBe|toHave|toEqual)\w*\s*\()")
_VALUE_BEARING_CALL = re.compile(r"(?:\bpage\.)?(fill|type|selectOption|setInputFiles|press)\s*\(")
_SELECTOR_CALL = re.compile(
    r"(?:\bpage\.|\.)(locator|getByRole|getByText|getByLabel|getByPlaceholder|"
    r"getByAltText|getByTitle|getByTestId)\s*\("
)


def _matching_paren(text: str, opening: int) -> int | None:
    """Return the matching parenthesis, ignoring quoted JavaScript strings."""
    depth = 0
    quote = ""
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _argument_spans(text: str, opening: int, closing: int) -> list[tuple[int, int]]:
    """Find top-level argument spans in a JavaScript call."""
    arguments: list[tuple[int, int]] = []
    start = opening + 1
    depth = 0
    quote = ""
    escaped = False
    for index in range(start, closing + 1):
        char = text[index] if index < closing else ","
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            left = start
            while left < index and text[left].isspace():
                left += 1
            right = index
            while right > left and text[right - 1].isspace():
                right -= 1
            if left != right:
                arguments.append((left, right))
            start = index + 1
    return arguments


def _masked_selector_line(text: str) -> str | None:
    """Mask selector arguments, returning None when a data call cannot be safely checked."""
    spans: list[tuple[int, int]] = []
    for match in _SELECTOR_CALL.finditer(text):
        opening = text.find("(", match.start(), match.end())
        closing = _matching_paren(text, opening)
        if closing is None:
            return None
        spans.extend(_argument_spans(text, opening, closing))

    for match in _VALUE_BEARING_CALL.finditer(text):
        opening = text.find("(", match.start(), match.end())
        closing = _matching_paren(text, opening)
        if closing is None:
            return None
        arguments = _argument_spans(text, opening, closing)
        # page.fill(selector, value) and related page methods take the selector first.
        if text[match.start() :].startswith("page."):
            if not arguments:
                return None
            spans.append(arguments[0])

    if _VALUE_BEARING_CALL.search(text) and not spans:
        # A locator-bound call has no selector argument of its own. Its data arguments
        # must therefore remain byte-for-byte unchanged.
        return text

    masked = text
    for start, end in reversed(sorted(spans)):
        masked = masked[:start] + "<selector>" + masked[end:]
    return masked


def _validate_value_bearing_calls(instruction: PatchInstruction) -> None:
    """Allow selector edits while preserving every input value supplied to Playwright."""
    original = _masked_selector_line(instruction.original)
    replacement = _masked_selector_line(instruction.replacement)
    if original is None or replacement is None or original != replacement:
        raise PatchApplicationError(
            f"line {instruction.line} changes input data for a value-bearing Playwright call"
        )


class PatchApplicationError(ValueError):
    """Raised when generated instructions do not match the current test code."""


def _validate_patch_scope(instruction: PatchInstruction) -> None:
    """Reject edits outside the single-line locator/wait guardrail."""
    if "\n" in instruction.replacement or "\r" in instruction.replacement:
        raise PatchApplicationError(
            f"line {instruction.line} replacement must contain exactly one line"
        )
    if _ASSERTION_CALL.search(instruction.original) or _ASSERTION_CALL.search(
        instruction.replacement
    ):
        raise PatchApplicationError(f"line {instruction.line} targets an assertion")
    if not _ALLOWED_PATCH_CALL.search(instruction.original) or not _ALLOWED_PATCH_CALL.search(
        instruction.replacement
    ):
        raise PatchApplicationError(
            f"line {instruction.line} is not limited to a locator or wait condition"
        )
    if _VALUE_BEARING_CALL.search(instruction.original) or _VALUE_BEARING_CALL.search(
        instruction.replacement
    ):
        _validate_value_bearing_calls(instruction)


def _apply(code: str, instructions: list[PatchInstruction]) -> str:
    """Validate and atomically apply line-targeted replacements to ``code``."""
    lines = code.splitlines(keepends=True)
    replacements: list[tuple[int, str]] = []
    targeted_lines: set[int] = set()
    for instruction in instructions:
        index = instruction.line - 1
        if instruction.line in targeted_lines:
            raise PatchApplicationError(f"line {instruction.line} is targeted more than once")
        targeted_lines.add(instruction.line)

        if not 0 <= index < len(lines):
            raise PatchApplicationError(
                f"line {instruction.line} is outside the current file ({len(lines)} line(s))"
            )

        current, line_ending = split_line_ending(lines[index])
        if current != instruction.original:
            raise PatchApplicationError(
                f"line {instruction.line} no longer matches the expected original text"
            )
        _validate_patch_scope(instruction)
        replacements.append((index, instruction.replacement + line_ending))

    for index, replacement in replacements:
        lines[index] = replacement
    return "".join(lines)


def patch_generator(state: AgentState) -> dict:
    """Generate a targeted patch via Structured Outputs and apply it to ``current_code``.

    On LLM/parse failure, log and return the code unchanged rather than crashing the
    graph — the Test Runner will fail again and the Router loops until the cap.
    """
    logger.info("patch_generator_started", loop_count=state["loop_count"])
    try:
        assert_patch_boundary_allowed(Path(state["test_script_path"]))
    except SandboxViolation as exc:
        logger.warning(
            "boundary_violation", test_script_path=state["test_script_path"], error=str(exc)
        )
        return {
            "current_code": state["current_code"],
            "patch_instructions": {},
            "analysis_report": state["analysis_report"] + f"\n\n[BOUNDARY FEEDBACK] {exc}",
            "boundary_report": {"ok": False, "error": str(exc)},
            "loop_count": state["loop_count"] + 1,
        }
    user_prompt = (
        f"Failure diagnosis:\n{state['analysis_report']}\n\n"
        f"Current test code:\n{state['current_code']}"
    )
    framework = state.get("detected_framework") or detect_framework(
        state["test_script_path"],
        state["current_code"],
        cast("list[DomDiffEntry]", state["dom_diff_context"]),
    )
    system_prompt = build_system_prompt(framework)
    try:
        output = generate_patch(system_prompt, user_prompt)
    except Exception:
        logger.exception("patch_generation_failed")
        return {
            "current_code": state["current_code"],
            "patch_instructions": {},
            "patch_application_report": {"ok": True},
        }

    try:
        patched = _apply(state["current_code"], output.instructions)
    except PatchApplicationError as exc:
        next_count = state["loop_count"] + 1
        logger.warning("patch_application_rejected", error=str(exc), loop_count=next_count)
        feedback = (
            "\n\n[PATCH APPLICATION FEEDBACK] The previous patch was not applied: "
            f"{exc}. Re-read the current test code and return its exact line text and line number."
        )
        return {
            "current_code": state["current_code"],
            "patch_instructions": {},
            "analysis_report": state["analysis_report"] + feedback,
            "patch_application_report": {"ok": False, "error": str(exc)},
            "loop_count": next_count,
        }
    logger.info("patch_generator_finished", instruction_count=len(output.instructions))
    return {
        "current_code": patched,
        "patch_instructions": output.model_dump(),
        "boundary_report": {"ok": True},
        "patch_application_report": {"ok": True},
    }
