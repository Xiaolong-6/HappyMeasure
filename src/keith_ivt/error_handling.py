"""Error handling utilities for HappyMeasure.

This module provides consistent error handling patterns across the application,
including user-friendly error messages, exception classification, and recovery
strategies.
"""
from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Any, Callable

from keith_ivt.logging_config import get_logger, handle_user_error


class ErrorSeverity(Enum):
    """Classification of error severity levels."""
    INFO = auto()           # Informational, no action needed
    WARNING = auto()        # Potential issue, but operation can continue
    ERROR = auto()          # Operation failed, user should retry
    CRITICAL = auto()       # System instability, restart may be needed


class ErrorCategory(Enum):
    """Classification of error types for appropriate handling."""
    HARDWARE = "hardware"
    FILE_IO = "file_io"
    NETWORK = "network"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    UI = "ui"
    UNKNOWN = "unknown"


class AppError(Exception):
    """Base application error with metadata for better handling.

    Attributes:
        message: Human-readable error message
        category: Type of error for routing to appropriate handler
        severity: How serious the error is
        context: Where the error occurred (module.function)
        original_exception: The underlying exception if this is wrapped
        recovery_suggestion: Optional suggestion for user recovery
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: str = "",
        original_exception: BaseException | None = None,
        recovery_suggestion: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context
        self.original_exception = original_exception
        self.recovery_suggestion = recovery_suggestion

        # Set __cause__ for exception chaining before logging
        if original_exception:
            self.__cause__ = original_exception

        # Log the error
        logger = get_logger("errors")
        log_msg = f"{context}: {message}" if context else message
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_msg, exc_info=original_exception)
        elif severity == ErrorSeverity.ERROR:
            logger.error(log_msg, exc_info=original_exception)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    def get_user_message(self) -> str:
        """Get a user-friendly version of the error message."""
        if self.recovery_suggestion:
            return f"{self.message}\n\n{self.recovery_suggestion}"
        return self.message


def classify_exception(exc: BaseException) -> tuple[ErrorCategory, ErrorSeverity]:
    """Classify an exception into category and severity.

    Args:
        exc: The exception to classify

    Returns:
        Tuple of (category, severity)
    """
    exc_name = type(exc).__name__.lower()
    exc_str = str(exc).lower()

    # Connection errors first (before file/io check since "connection" might match io patterns)
    if "connection" in exc_name:
        return ErrorCategory.HARDWARE, ErrorSeverity.CRITICAL
    
    # Hardware errors
    if any(kw in exc_name or kw in exc_str for kw in ["serial", "instrument", "keithley", "smu"]):
        if "timeout" in exc_str or "not found" in exc_str:
            return ErrorCategory.HARDWARE, ErrorSeverity.ERROR
        return ErrorCategory.HARDWARE, ErrorSeverity.CRITICAL

    # File I/O errors
    if any(kw in exc_name or kw in exc_str for kw in ["file", "permission", "denied"]):
        return ErrorCategory.FILE_IO, ErrorSeverity.ERROR
    
    # Network errors
    if any(kw in exc_name or kw in exc_str for kw in ["network", "socket"]):
        return ErrorCategory.NETWORK, ErrorSeverity.ERROR
    
    # Timeout errors
    if "timeout" in exc_name or "timeout" in exc_str:
        return ErrorCategory.HARDWARE, ErrorSeverity.ERROR

    # Validation errors
    if any(kw in exc_name or kw in exc_str for kw in ["value", "type", "invalid", "validate"]):
        return ErrorCategory.VALIDATION, ErrorSeverity.WARNING

    # Configuration errors
    if any(kw in exc_name or kw in exc_str for kw in ["config", "setting", "parse"]):
        return ErrorCategory.CONFIGURATION, ErrorSeverity.WARNING

    # Default
    return ErrorCategory.UNKNOWN, ErrorSeverity.ERROR


def safe_execute(
    func: Callable[..., Any],
    *args: Any,
    error_message: str = "Operation failed",
    context: str = "",
    default_return: Any = None,
    **kwargs: Any,
) -> Any:
    """Execute a function with comprehensive error handling.

    This wrapper catches exceptions, logs them appropriately, and returns
    a default value instead of crashing.

    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        error_message: Message to show if operation fails
        context: Context string for logging
        default_return: Value to return on failure
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Function result, or default_return on failure

    Usage:
        >>> result = safe_execute(
        ...     connect_to_hardware,
        ...     port="COM3",
        ...     error_message="Failed to connect",
        ...     context="Hardware.connect",
        ...     default_return=None
        ... )
        >>> if result is None:
        ...     show_error_to_user()
    """
    logger = get_logger("safe_execute")

    try:
        return func(*args, **kwargs)
    except AppError as e:
        # Already classified application error
        logger.warning(f"{context}: {e.message}")
        return default_return
    except Exception as e:
        # Classify and handle unexpected errors
        category, severity = classify_exception(e)
        logger.error(f"{context}: {error_message} - {type(e).__name__}: {e}", exc_info=True)

        # For critical errors, re-raise to allow higher-level handling
        if severity == ErrorSeverity.CRITICAL:
            raise AppError(
                message=f"{error_message}: {e}",
                category=category,
                severity=severity,
                context=context,
                original_exception=e,
            ) from e

        return default_return


def create_error_recovery_handler(
    logger_name: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Callable[[Callable[..., Any], dict[str, Any]], Any]:
    """Create a retry-based error recovery handler.

    Args:
        logger_name: Name for the logger
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        A decorator function that adds retry logic

    Usage:
        >>> @create_error_recovery_handler("hardware_ops", max_retries=3)
        ... def read_instrument():
        ...     # May fail intermittently
        ...     pass
    """
    import time

    logger = logging.getLogger(logger_name)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {retry_delay}s..."
                        )
                        time.sleep(retry_delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}",
                            exc_info=True,
                        )

            # All retries exhausted
            raise last_exception

        return wrapper

    return decorator


# Export commonly used functions
__all__ = [
    "AppError",
    "ErrorSeverity",
    "ErrorCategory",
    "classify_exception",
    "safe_execute",
    "handle_user_error",
    "create_error_recovery_handler",
]
