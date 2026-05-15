from __future__ import annotations

import datetime as _dt
import io
import logging
import sys
import traceback
from pathlib import Path
from typing import TextIO

from keith_ivt.data.logging_utils import AppLog
from keith_ivt.logging_config import setup_logging

_LOG_DIR = Path("logs")
_CONSOLE_LOG = _LOG_DIR / "console_last_run.log"
_RUNTIME_ERRORS = _LOG_DIR / "error.log"
_APP_LOG = _LOG_DIR / "log.txt"
_INSTALLED = False
_EXCEPTHOOK_INSTALLED = False


def _runtime_logger(log_dir: str | Path = _LOG_DIR) -> logging.Logger:
    """Return the central runtime logger, configuring it on first use."""
    logger = logging.getLogger("keith_ivt.runtime")
    root = logging.getLogger("keith_ivt")
    if not root.handlers:
        setup_logging(log_dir=Path(log_dir), console_output=False)
    return logger


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class TeeTextIO(io.TextIOBase):
    """Write text to the original stream and to a log file.

    The class is intentionally tiny. It is used during offline-alpha debugging so
    command-prompt tracebacks are not lost when a user only sees a brief console
    flash or closes the window.
    """

    def __init__(self, original: TextIO, log_file: TextIO) -> None:
        self.original = original
        self.log_file = log_file

    @property
    def encoding(self):  # pragma: no cover - delegates to host console
        return getattr(self.original, "encoding", "utf-8")

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        try:
            self.original.write(text)
        finally:
            self.log_file.write(text)
            self.log_file.flush()
        return len(text)

    def flush(self) -> None:
        self.original.flush()
        self.log_file.flush()


def install_console_logging(log_dir: str | Path = _LOG_DIR) -> None:
    """Mirror stdout/stderr to logs/console_last_run.log for the current run."""
    global _INSTALLED
    if _INSTALLED:
        return
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    console_file = (log_dir / "console_last_run.log").open("w", encoding="utf-8", buffering=1)
    console_file.write(f"[{_stamp()}] HappyMeasure console capture started.\n")
    sys.stdout = TeeTextIO(sys.stdout, console_file)  # type: ignore[assignment]
    sys.stderr = TeeTextIO(sys.stderr, console_file)  # type: ignore[assignment]
    _INSTALLED = True


def log_runtime_error(message: str, exc: BaseException | None = None, log_dir: str | Path = _LOG_DIR) -> None:
    """Log runtime errors through the central logging configuration."""
    logger = _runtime_logger(log_dir)
    if exc is not None:
        logger.error(message, exc_info=(type(exc), exc, exc.__traceback__))
    else:
        logger.error(message)


def install_excepthook(log_dir: str | Path = _LOG_DIR) -> None:
    """Persist uncaught exceptions before the default traceback is shown.

    Idempotent installation prevents duplicated runtime error records if the
    launcher or a test imports the entry point more than once.
    """
    global _EXCEPTHOOK_INSTALLED
    if _EXCEPTHOOK_INSTALLED:
        return
    old_hook = sys.excepthook

    def _hook(exc_type, exc, tb):
        log_runtime_error("Uncaught exception", exc, log_dir=log_dir)
        old_hook(exc_type, exc, tb)

    sys.excepthook = _hook
    _EXCEPTHOOK_INSTALLED = True


def install_tk_exception_logging(root, log_dir: str | Path = _LOG_DIR) -> None:
    """Capture Tk callback exceptions, which otherwise only print to stderr."""
    def _report(exc_type, exc, tb):
        logger = _runtime_logger(log_dir)
        logger.error("Tk callback exception", exc_info=(exc_type, exc, tb))
        traceback.print_exception(exc_type, exc, tb)

    root.report_callback_exception = _report


def append_app_event(text: str, log_dir: str | Path = _LOG_DIR) -> None:
    """Append a UI/app event through the same AppLog writer used by the UI."""
    AppLog(path=Path(log_dir) / "log.txt").write(text)
    _runtime_logger(log_dir).info(text)
