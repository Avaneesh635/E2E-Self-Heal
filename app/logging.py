"""structlog configuration for the whole application."""

import logging
import sys
from typing import TextIO, cast

import structlog


class _CurrentStderr:
    """Write to whatever ``sys.stderr`` is at write time, not when logging was configured.

    Loggers are cached on first use, so a stream bound at configure time outlives any later
    replacement of ``sys.stderr`` (a test runner's capture, for example) and can be closed.
    """

    def write(self, text: str) -> int:
        return sys.stderr.write(text)

    def flush(self) -> None:
        sys.stderr.flush()


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog once at process start.

    Logs go to stderr, never stdout: ``--json`` writes the machine-readable result to stdout
    and CI redirects it to a file (``e2e-healer ... --json > repair-summary.json``), so any
    log line there would make that file invalid JSON.
    """
    logging.basicConfig(format="%(message)s", level=level, stream=sys.stderr)
    structlog.configure(
        logger_factory=structlog.PrintLoggerFactory(file=cast(TextIO, _CurrentStderr())),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        cache_logger_on_first_use=True,
    )
