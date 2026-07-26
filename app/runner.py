"""Shared Playwright execution helper.

Used both by the CLI's initial failure capture and by the Test Runner node, so the
subprocess invocation lives in exactly one place.
"""

import shlex
import subprocess

import structlog

from app.config import settings
from app.sandbox import assert_command_allowed

logger = structlog.get_logger(__name__)


def _as_text(stream: str | bytes | None) -> str:
    """Coerce captured subprocess output to text (it is bytes when a timeout kills the run)."""
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode(errors="replace")
    return stream


def run_playwright(test_path: str = "") -> tuple[bool, str]:
    """Run Playwright against a single test file, or the whole suite if ``test_path`` is empty.

    Returns ``(passed, combined_log)`` where stdout and stderr are merged so the
    Error Log Parser sees the full failure output.
    """
    cmd = [*shlex.split(settings.playwright_cmd), *([test_path] if test_path else [])]
    assert_command_allowed(cmd, reason="playwright")
    timeout = settings.test_timeout_seconds
    logger.info("playwright_run_started", cmd=cmd, timeout=timeout)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        # A hung run (dead dev server, deadlocked waitForSelector, orphaned browser) must not
        # block the repair loop. Kill it and surface it as an ordinary test failure so the
        # caller refreshes error_log and increments loop_count — never crash the graph.
        logger.warning("test_run_timeout", path=test_path, timeout=timeout)
        partial = _as_text(exc.stdout) + _as_text(exc.stderr)
        log = f"{partial}\nError: test run timed out after {timeout}s and was killed.".strip()
        return False, log

    passed = result.returncode == 0
    log = result.stdout + result.stderr
    logger.info("playwright_run_finished", passed=passed, returncode=result.returncode)
    return passed, log
