"""Best-effort Windows system-sleep prevention for active measurements.

The guard deliberately requests only ``ES_SYSTEM_REQUIRED``.  Windows may still
turn the display off, and user-initiated lock, sleep, lid-close, or power-button
actions remain outside this application's control.
"""

from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable
from typing import Literal

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

LogCallback = Callable[[str], None]
ExecutionStateSetter = Callable[[int], int]


class SystemSleepGuard:
    """Request Windows system-awake execution state for one worker lifetime.

    API discovery and calls are intentionally best-effort.  A missing API,
    unsupported platform, or failed request is logged and treated as a degraded
    no-op so a measurement can continue safely.
    """

    def __init__(
        self,
        logger: LogCallback | None = None,
        *,
        platform: str | None = None,
        set_thread_execution_state: ExecutionStateSetter | None = None,
    ) -> None:
        self._logger = logger
        self._platform = sys.platform if platform is None else platform
        self._setter = set_thread_execution_state
        self.active = False

    def _log(self, message: str) -> None:
        if self._logger is None:
            return
        try:
            self._logger(message)
        except Exception:
            # Logging must never turn a best-effort power guard into a
            # measurement failure.
            pass

    def _resolve_setter(self) -> ExecutionStateSetter:
        if self._setter is not None:
            return self._setter
        if self._platform != "win32":
            raise OSError("Windows execution-state API is unavailable on this platform")
        setter = ctypes.windll.kernel32.SetThreadExecutionState
        setter.argtypes = [ctypes.c_uint]
        setter.restype = ctypes.c_uint
        self._setter = setter
        return setter

    def __enter__(self) -> "SystemSleepGuard":
        if self._platform != "win32":
            self._log(
                "System sleep prevention unavailable on this platform; measurement continues."
            )
            return self
        try:
            setter = self._resolve_setter()
            result = setter(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            if not result:
                raise OSError("SetThreadExecutionState returned failure")
            self.active = True
            self._log("System sleep prevention enabled for active measurement.")
        except Exception as exc:
            self._log(f"System sleep prevention request failed: {exc}; measurement continues.")
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        if self._platform != "win32" or self._setter is None:
            return False
        try:
            result = self._setter(ES_CONTINUOUS)
            if not result:
                self._log("System sleep prevention release failed; measurement cleanup continues.")
            else:
                self._log("System sleep prevention released.")
        except Exception as release_exc:
            self._log(
                f"System sleep prevention release failed: {release_exc}; measurement cleanup continues."
            )
        finally:
            self.active = False
        return False


def prevent_system_sleep(
    logger: LogCallback | None = None,
    *,
    platform: str | None = None,
    set_thread_execution_state: ExecutionStateSetter | None = None,
) -> SystemSleepGuard:
    """Return a best-effort context guard for one active measurement."""
    return SystemSleepGuard(
        logger,
        platform=platform,
        set_thread_execution_state=set_thread_execution_state,
    )


__all__ = [
    "ES_CONTINUOUS",
    "ES_SYSTEM_REQUIRED",
    "SystemSleepGuard",
    "prevent_system_sleep",
]
