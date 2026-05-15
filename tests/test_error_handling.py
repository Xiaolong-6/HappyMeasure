"""Tests for error handling and logging system."""
import logging
import pytest
from pathlib import Path
import tempfile
import shutil

from keith_ivt.logging_config import (
    setup_logging,
    get_logger,
    log_exception,
    handle_user_error,
)
from keith_ivt.error_handling import (
    AppError,
    ErrorSeverity,
    ErrorCategory,
    classify_exception,
    safe_execute,
    create_error_recovery_handler,
)


class TestLoggingSetup:
    """Test logging configuration."""

    def test_setup_logging_creates_files(self):
        """Logging setup should create log directory and files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            try:
                logger = setup_logging(
                    log_dir=log_dir,
                    level=logging.INFO,
                    console_output=False,  # Disable console for tests
                )

                assert log_dir.exists()
                assert (log_dir / "app.log").exists()
                assert (log_dir / "error.log").exists()
            finally:
                for handler in list(logging.getLogger("keith_ivt").handlers):
                    logging.getLogger("keith_ivt").removeHandler(handler)
                    handler.close()
                logging.shutdown()

    def test_get_logger_returns_package_logger(self):
        """get_logger should return properly namespaced logger."""
        logger = get_logger("test_module")
        assert logger.name == "keith_ivt.test_module"

    def test_logging_writes_to_file(self):
        """Log messages should be written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            try:
                logger = setup_logging(
                    log_dir=log_dir,
                    level=logging.DEBUG,
                    console_output=False,
                )

                test_message = "Test log message"
                logger.info(test_message)

                # Force flush
                for handler in logger.handlers:
                    handler.flush()

                # Check file contents
                log_file = log_dir / "app.log"
                content = log_file.read_text()
                assert test_message in content
            finally:
                for handler in list(logging.getLogger("keith_ivt").handlers):
                    logging.getLogger("keith_ivt").removeHandler(handler)
                    handler.close()
                logging.shutdown()


class TestAppError:
    """Test custom application error class."""

    def test_app_error_basic_properties(self):
        """AppError should store metadata correctly."""
        error = AppError(
            message="Test error",
            category=ErrorCategory.HARDWARE,
            severity=ErrorSeverity.ERROR,
            context="test.function",
        )

        assert error.message == "Test error"
        assert error.category == ErrorCategory.HARDWARE
        assert error.severity == ErrorSeverity.ERROR
        assert error.context == "test.function"
        assert str(error) == "Test error"

    def test_app_error_with_original_exception(self):
        """AppError should preserve original exception."""
        original = ValueError("Original error")
        error = AppError(
            message="Wrapped error",
            original_exception=original,
        )

        assert error.original_exception is original
        assert error.__cause__ is original

    def test_app_error_user_message(self):
        """get_user_message should include recovery suggestion if present."""
        error = AppError(
            message="Operation failed",
            recovery_suggestion="Please try again",
        )

        user_msg = error.get_user_message()
        assert "Operation failed" in user_msg
        assert "Please try again" in user_msg


class TestExceptionClassification:
    """Test exception classification logic."""

    def test_classify_hardware_timeout(self):
        """Hardware timeout should be classified correctly."""
        exc = TimeoutError("Serial port timeout")
        category, severity = classify_exception(exc)
        assert category == ErrorCategory.HARDWARE
        assert severity == ErrorSeverity.ERROR

    def test_classify_file_not_found(self):
        """File not found should be classified as FILE_IO."""
        exc = FileNotFoundError("File not found")
        category, severity = classify_exception(exc)
        assert category == ErrorCategory.FILE_IO
        assert severity == ErrorSeverity.ERROR

    def test_classify_value_error(self):
        """Value errors should be VALIDATION warnings."""
        exc = ValueError("Invalid value")
        category, severity = classify_exception(exc)
        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.WARNING

    def test_classify_unknown_exception(self):
        """Unknown exceptions should default to UNKNOWN/ERROR."""
        exc = RuntimeError("Generic error")
        category, severity = classify_exception(exc)
        assert category == ErrorCategory.UNKNOWN
        assert severity == ErrorSeverity.ERROR


class TestSafeExecute:
    """Test safe execution wrapper."""

    def test_safe_execute_success(self):
        """safe_execute should return function result on success."""
        def add(a, b):
            return a + b

        result = safe_execute(add, 2, 3, context="test.add")
        assert result == 5

    def test_safe_execute_returns_default_on_error(self):
        """safe_execute should return default value on failure."""
        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(
            failing_func,
            error_message="Failed",
            context="test.failing",
            default_return=None,
        )
        assert result is None

    def test_safe_execute_reraises_critical(self):
        """safe_execute should re-raise critical errors as AppError."""
        def critical_failure():
            raise ConnectionError("Critical hardware failure")

        with pytest.raises(AppError) as exc_info:
            safe_execute(
                critical_failure,
                error_message="Critical fail",
                context="test.critical",
            )

        assert exc_info.value.severity == ErrorSeverity.CRITICAL


class TestHandleUserError:
    """Test user-friendly error message generation."""

    def test_serial_port_not_found(self):
        """Should provide helpful message for missing COM port."""
        msg = handle_user_error(
            "Port not found",
            context="Hardware.connect",
        )
        assert "COM port" in msg
        assert "connected" in msg.lower()

    def test_permission_denied(self):
        """Should explain permission issues clearly."""
        msg = handle_user_error(
            "Access denied",
            context="File operation",
        )
        assert "permission" in msg.lower() or "access" in msg.lower()

    def test_generic_error(self):
        """Should provide generic fallback message."""
        msg = handle_user_error(
            "Something went wrong",
            context="Unknown operation",
        )
        assert "logged" in msg.lower()


class TestErrorRecoveryHandler:
    """Test retry-based error recovery."""

    def test_retry_on_failure_then_success(self):
        """Should retry until success."""
        call_count = 0

        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        handler = create_error_recovery_handler("test_retry", max_retries=3, retry_delay=0.01)
        decorated = handler(flaky_function)

        result = decorated()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted_raises_last_exception(self):
        """Should raise last exception after all retries fail."""
        def always_fails():
            raise ValueError("Always fails")

        handler = create_error_recovery_handler("test_retry", max_retries=2, retry_delay=0.01)
        decorated = handler(always_fails)

        with pytest.raises(ValueError, match="Always fails"):
            decorated()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
