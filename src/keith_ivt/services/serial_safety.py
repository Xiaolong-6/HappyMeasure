from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SerialRetryPolicy:
    """Small retry/backoff policy for real serial hardware commands.

    The policy is intentionally conservative for alpha hardware bring-up: retry
    transient serial timeouts a few times, but never hide the final failure.  It
    accepts an optional logger callback so UI/controller code can record the
    command and retry count without coupling this module to Tk.
    """

    max_attempts: int = 3
    base_delay_s: float = 0.15
    backoff_factor: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay_s < 0:
            raise ValueError("base_delay_s must be non-negative")
        if self.backoff_factor < 1:
            raise ValueError("backoff_factor must be >= 1")

    def run(self, action: Callable[[], T], *, label: str = "serial command", logger: Callable[[str], None] | None = None) -> T:
        last_exc: BaseException | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return action()
            except Exception as exc:  # hardware libraries use several exception classes
                last_exc = exc
                if attempt >= self.max_attempts:
                    break
                delay = self.base_delay_s * (self.backoff_factor ** (attempt - 1))
                if logger is not None:
                    logger(f"{label} failed on attempt {attempt}/{self.max_attempts}: {exc}; retrying in {delay:.2f}s")
                if delay > 0:
                    time.sleep(delay)
        assert last_exc is not None
        raise last_exc


class OutputOffGuard:
    """Best-effort output-off helper used in shutdown/error paths."""

    def __init__(self, logger: Callable[[str], None] | None = None) -> None:
        self.logger = logger

    def turn_off(self, output_off: Callable[[], None], *, context: str = "shutdown") -> bool:
        try:
            output_off()
            return True
        except Exception as exc:
            if self.logger is not None:
                self.logger(f"Output OFF failed during {context}: {exc}")
            return False
