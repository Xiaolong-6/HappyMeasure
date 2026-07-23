from __future__ import annotations

from dataclasses import dataclass, replace
from queue import Empty, SimpleQueue
import threading
import time
from typing import Literal

CURRENT_RANGE_OPTIONS_A: tuple[float, ...] = (
    1e-12,
    10e-12,
    100e-12,
    1e-9,
    10e-9,
    100e-9,
    1e-6,
    10e-6,
    100e-6,
    1e-3,
    10e-3,
    100e-3,
)


def format_current_range(value_A: float | None) -> str:
    if value_A is None:
        return "Unknown"
    value = abs(float(value_A))
    for scale, unit in ((1e-3, "mA"), (1e-6, "uA"), (1e-9, "nA"), (1e-12, "pA")):
        if value >= scale * 0.999 or scale == 1e-12:
            scaled = value / scale
            if abs(scaled - round(scaled)) < 1e-9:
                return f"{int(round(scaled))} {unit}"
            return f"{scaled:.3g} {unit}"
    return f"{value:.3g} A"


def current_range_labels() -> list[str]:
    return [f"{format_current_range(value)} ({value:.0e} A)" for value in CURRENT_RANGE_OPTIONS_A]


def parse_current_range_label(label: str) -> float | None:
    text = str(label).strip()
    for value in CURRENT_RANGE_OPTIONS_A:
        if text.startswith(format_current_range(value)):
            return value
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class CurrentRangeState:
    autorange: bool | None = None
    actual_range_A: float | None = None
    fixed_range_A: float | None = None
    last_change_monotonic_s: float | None = None
    warning: str | None = None

    def headline(self) -> str:
        actual = format_current_range(self.actual_range_A)
        if self.autorange is True:
            return f"Current range: AUTO, actual {actual}"
        if self.autorange is False:
            return f"Current range: FIXED {format_current_range(self.fixed_range_A or self.actual_range_A)}"
        return f"Current range: Unknown, actual {actual}"

    def status_fragment(self) -> str:
        if self.autorange is True:
            return f"Auto/{format_current_range(self.actual_range_A)}"
        if self.autorange is False:
            return f"Fixed/{format_current_range(self.fixed_range_A or self.actual_range_A)}"
        return "Unknown"

    def last_change_text(self, now_s: float | None = None) -> str:
        if self.last_change_monotonic_s is None:
            return "none"
        now = time.monotonic() if now_s is None else float(now_s)
        return f"{max(0.0, now - self.last_change_monotonic_s):.1f} s ago"


RangeActionKind = Literal["autorange", "fixed_range", "lock_current"]


@dataclass(frozen=True)
class CurrentRangeAction:
    kind: RangeActionKind
    value: bool | float | None = None


class CurrentRangeControl:
    def __init__(self, state: CurrentRangeState | None = None):
        self._state = state or CurrentRangeState()
        self._lock = threading.Lock()
        self._pending: SimpleQueue[CurrentRangeAction] = SimpleQueue()

    def snapshot(self) -> CurrentRangeState:
        with self._lock:
            return self._state

    def update_state(self, state: CurrentRangeState) -> CurrentRangeState:
        with self._lock:
            previous = self._state
            changed = (
                previous.actual_range_A is not None
                and state.actual_range_A is not None
                and abs(previous.actual_range_A - state.actual_range_A)
                > max(1e-15, abs(previous.actual_range_A) * 1e-6)
            )
            if changed and state.last_change_monotonic_s is None:
                state = replace(state, last_change_monotonic_s=time.monotonic())
            self._state = state
            return state

    def with_warning(self, warning: str) -> CurrentRangeState:
        with self._lock:
            self._state = replace(self._state, warning=warning)
            return self._state

    def request_autorange(self, enabled: bool) -> None:
        self._pending.put(CurrentRangeAction("autorange", bool(enabled)))

    def request_fixed_range(self, range_A: float) -> None:
        self._pending.put(CurrentRangeAction("fixed_range", float(range_A)))

    def request_lock_current(self) -> None:
        self._pending.put(CurrentRangeAction("lock_current", None))

    def drain_actions(self) -> list[CurrentRangeAction]:
        actions: list[CurrentRangeAction] = []
        while True:
            try:
                actions.append(self._pending.get_nowait())
            except Empty:
                return actions
