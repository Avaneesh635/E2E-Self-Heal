import io
import sys
from collections.abc import Iterator

import pytest
import structlog

from app.logging import configure_logging


@pytest.fixture
def restore_structlog_config() -> Iterator[None]:
    """configure_logging binds the current sys.stderr; put the global config back afterwards."""
    saved = structlog.get_config()
    yield
    structlog.configure(**saved)


def test_log_output_goes_to_stderr_never_stdout(
    capsys: pytest.CaptureFixture[str], restore_structlog_config: None
) -> None:
    # `--json` writes the result to stdout and CI redirects it into a file, so a single log
    # line on stdout would make that file invalid JSON.
    configure_logging("INFO")

    structlog.get_logger("probe").info("probe_event", answer=42)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "probe_event" in captured.err


def test_a_cached_logger_follows_sys_stderr_after_it_is_replaced(
    monkeypatch: pytest.MonkeyPatch, restore_structlog_config: None
) -> None:
    # Loggers are cached on first use. If the stream were bound when logging is configured,
    # replacing sys.stderr later (as a CLI test runner does) would leave a cached logger
    # writing to a stale, possibly closed, stream.
    first = io.StringIO()
    monkeypatch.setattr(sys, "stderr", first)
    configure_logging("INFO")
    logger = structlog.get_logger("cached_probe")
    logger.info("first_event")
    first.close()

    second = io.StringIO()
    monkeypatch.setattr(sys, "stderr", second)
    logger.info("second_event")

    assert "second_event" in second.getvalue()
