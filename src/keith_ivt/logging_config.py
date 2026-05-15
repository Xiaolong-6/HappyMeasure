"""Structured logging configuration for HappyMeasure.

This module sets up Python's standard logging framework with:
- Structured JSON logging for machine parsing
- Rotating file handlers to manage disk space
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Separate error log for quick diagnostics
- Console output during development
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Log format strings
SIMPLE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DETAILED_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d in %(funcName)s(): %(message)s"

# Default log directory
DEFAULT_LOG_DIR = Path("logs")


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for structured analysis.

    This formatter produces machine-readable JSON logs that can be easily
    parsed by log aggregation tools, making it simpler to search and filter
    logs programmatically.

    Example output:
        {
            "timestamp": "2026-05-14T10:30:45.123456+08:00",
            "level": "ERROR",
            "logger": "keith_ivt.hardware_controller",
            "message": "Failed to connect to instrument",
            "module": "hardware_controller",
            "function": "connect_instrument",
            "line": 142,
            "exception": "SerialException: Port COM3 not found"
        }
    """

    def format(self, record: logging.LogRecord) -> str:
        # Build base structure
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[1]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)


class ContextFilter(logging.Filter):
    """Add contextual information to log records.

    This filter can add user ID, session ID, or other runtime context
    to every log message for better traceability.
    """

    def __init__(self, context: dict[str, str] | None = None):
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        # Add context to each log record
        for key, value in self.context.items():
            setattr(record, f"ctx_{key}", value)
        return True


def setup_logging(
    log_dir: Path = DEFAULT_LOG_DIR,
    level: int = logging.INFO,
    use_json: bool = False,
    max_bytes: int = 1_000_000,  # 1 MB
    backup_count: int = 5,
    console_output: bool = True,
) -> logging.Logger:
    """Configure application-wide logging.

    Args:
        log_dir: Directory for log files
        level: Minimum log level to capture
        use_json: Whether to use JSON formatting (False = human-readable)
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of rotated log files to keep
        console_output: Whether to also output to console

    Returns:
        Root logger for the application

    Usage:
        >>> from keith_ivt.logging_config import setup_logging
        >>> logger = setup_logging()
        >>> logger.info("Application started")
        >>> logger.error("Connection failed", exc_info=True)
    """
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get root logger for our package
    root_logger = logging.getLogger("keith_ivt")
    root_logger.setLevel(level)

    # Reconfigure cleanly on repeated setup calls. Test runs and app restarts may
    # request a different log directory; returning old handlers would write to
    # stale files and make the requested log path appear missing.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass
    root_logger.filters.clear()

    # Choose formatter
    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(DETAILED_FORMAT)

    # Main application log (rotating)
    main_log_file = log_dir / "app.log"
    main_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    main_handler.setLevel(level)
    main_handler.setFormatter(formatter)
    root_logger.addHandler(main_handler)

    # Error-only log (separate file for quick diagnostics)
    error_log_file = log_dir / "error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Console handler (for development/debugging)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        # Use simpler format for console
        console_formatter = logging.Formatter(SIMPLE_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Add context filter
    try:
        from keith_ivt.version import __version__
    except Exception:  # pragma: no cover - defensive during early startup
        __version__ = "unknown"
    context_filter = ContextFilter({
        "version": __version__,
    })
    root_logger.addFilter(context_filter)

    # Capture warnings from other libraries
    logging.captureWarnings(True)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance for the module

    Usage:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
        >>> logger.info("Info message")
        >>> logger.warning("Warning message")
        >>> logger.error("Error message", exc_info=True)
        >>> logger.critical("Critical message")
    """
    return logging.getLogger(f"keith_ivt.{name}")


def log_exception(logger: logging.Logger, message: str, exc: BaseException | None = None) -> None:
    """Convenience function to log exceptions with full traceback.

    Args:
        logger: Logger instance
        message: Human-readable error message
        exc: Exception to log (uses sys.exc_info() if None)

    Usage:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception(logger, "Operation failed", e)
    """
    if exc:
        logger.error(f"{message}: {exc}", exc_info=exc)
    else:
        logger.error(message, exc_info=True)


def install_tk_error_handling(root, logger: logging.Logger | None = None) -> None:
    """Install Tkinter callback exception handler.

    Tkinter swallows exceptions in callbacks by default. This installs a
    handler that logs them properly.

    Args:
        root: Tk root window
        logger: Logger to use (creates one if None)
    """
    if logger is None:
        logger = get_logger("ui.tk_errors")

    def _report_callback_exception(exc_type, exc_value, exc_tb):
        """Handle uncaught Tk callback exceptions."""
        # Format full traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        tb_str = "".join(tb_lines)

        # Log the exception
        logger.critical(
            f"Uncaught Tk callback exception: {exc_type.__name__}: {exc_value}\n{tb_str}"
        )

        # Still show traceback to console for debugging
        traceback.print_exception(exc_type, exc_value, exc_tb)

    # Install the handler
    root.report_callback_exception = _report_callback_exception


def handle_user_error(message: str, exc: BaseException | None = None, context: str = "") -> str:
    """Create user-friendly error messages from technical exceptions.

    This function maps common technical errors to user-friendly messages
    while still logging the full details for developers.

    Args:
        message: Technical error message or context
        exc: The exception that occurred
        context: Additional context about where the error occurred

    Returns:
        User-friendly error message suitable for display

    Usage:
        >>> try:
        ...     connect_to_hardware()
        ... except SerialException as e:
        ...     user_msg = handle_user_error("Connection failed", e, "Hardware.connect")
        ...     messagebox.showerror("Error", user_msg)
    """
    logger = get_logger("errors.user_facing")

    # Log full details for developers
    if exc:
        logger.error(f"{context}: {message}", exc_info=exc)
    else:
        logger.error(f"{context}: {message}")

    # Map common errors to user-friendly messages
    error_lower = message.lower()
    exc_str = str(exc).lower() if exc else ""

    # Hardware/serial errors
    if any(kw in error_lower or kw in exc_str for kw in ["serial", "port", "com"]):
        if "not found" in error_lower or "no such file" in exc_str:
            return "Cannot find the specified COM port. Please check:\n1. The instrument is connected\n2. The correct COM port is selected\n3. Drivers are installed"
        elif "permission" in error_lower or "access denied" in exc_str:
            return "Cannot access the COM port. It may be in use by another program.\nPlease close other applications and try again."
        elif "timeout" in error_lower:
            return "Communication timeout. The instrument is not responding.\nCheck the connection and try again."

    # File I/O errors
    if any(kw in error_lower or kw in exc_str for kw in ["file", "permission", "denied"]):
        if "permission" in error_lower or "denied" in exc_str:
            return "Cannot access the file. Please check file permissions and try again."
        elif "not found" in error_lower:
            return "File not found. Please verify the path and try again."

    # Generic fallback
    if context:
        return f"{context} failed.\n\nDetails have been logged for troubleshooting.\n\nTechnical: {message}"
    return f"Operation failed.\n\nDetails have been logged for troubleshooting.\n\nTechnical: {message}"


def create_diagnostic_report(log_dir: Path = DEFAULT_LOG_DIR) -> Path:
    """Create a diagnostic report zip file for support.

    Collects recent logs, system info, and configuration into a single
    archive that can be sent to support for troubleshooting.

    Args:
        log_dir: Directory containing log files

    Returns:
        Path to the created diagnostic zip file
    """
    import zipfile

    logger = get_logger("diagnostics")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = log_dir / f"diagnostic_report_{timestamp}.zip"

    try:
        with zipfile.ZipFile(report_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add log files
            for log_file in log_dir.glob("*.log"):
                if log_file != report_path:  # Don't include the report itself
                    try:
                        zf.write(log_file, arcname=f"logs/{log_file.name}")
                    except OSError as e:
                        logger.warning(f"Could not add {log_file}: {e}")

            # Add system info
            import platform
            import sys

            sys_info = f"""Platform: {platform.platform()}
Python: {sys.version}
Working Directory: {Path.cwd()}
Timestamp: {datetime.now().isoformat()}
"""
            zf.writestr("system_info.txt", sys_info)

        logger.info(f"Diagnostic report created: {report_path}")
        return report_path

    except Exception as e:
        logger.error(f"Failed to create diagnostic report: {e}", exc_info=True)
        raise
