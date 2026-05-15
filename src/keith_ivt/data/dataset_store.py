from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from itertools import count

from keith_ivt.models import SweepResult

_id_counter = count(1)
_TRACE_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


@dataclass
class DeviceTrace:
    """UI-level dataset wrapper for one completed sweep.

    This intentionally has no hardware dependency. Real Keithley sweeps,
    simulated sweeps, and later imported CSV files can all enter the UI through
    the same SweepResult -> DeviceTrace path.
    """

    result: SweepResult
    name: str
    trace_id: int = field(default_factory=lambda: next(_id_counter))
    visible: bool = True
    color: str = "#1f77b4"
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def point_count(self) -> int:
        return len(self.result.points)

    @property
    def label(self) -> str:
        mode = self.result.config.mode.value
        suffix = "visible" if self.visible else "hidden"
        return f"{self.name} | {mode} | {self.point_count} pts | {suffix}"


class DatasetStore:
    """Small in-memory trace registry for alpha UI development."""

    def __init__(self) -> None:
        self._traces: list[DeviceTrace] = []

    def add_result(self, result: SweepResult, name: str | None = None) -> DeviceTrace:
        base_name = (name or result.config.device_name or "Device").strip()
        unique_name = self._unique_name(base_name)
        color = _TRACE_COLORS[len(self._traces) % len(_TRACE_COLORS)]
        trace = DeviceTrace(result=result, name=unique_name, color=color)
        self._traces.append(trace)
        return trace

    def all(self) -> list[DeviceTrace]:
        # Return in reverse order so newest traces appear first in the UI
        return list(reversed(self._traces))

    def get(self, trace_id: int) -> DeviceTrace | None:
        return next((trace for trace in self._traces if trace.trace_id == trace_id), None)

    def remove(self, trace_id: int) -> None:
        self._traces = [trace for trace in self._traces if trace.trace_id != trace_id]

    def clear(self) -> None:
        self._traces.clear()

    def rename(self, trace_id: int, new_name: str) -> None:
        trace = self.get(trace_id)
        if trace is None:
            return
        clean_name = new_name.strip()
        if not clean_name:
            return
        trace.name = self._unique_name(clean_name, exclude_id=trace_id)

    def toggle_visibility(self, trace_id: int) -> None:
        trace = self.get(trace_id)
        if trace is not None:
            trace.visible = not trace.visible

    def set_color(self, trace_id: int, color: str) -> None:
        trace = self.get(trace_id)
        if trace is not None and color:
            trace.color = color

    def _unique_name(self, base_name: str, exclude_id: int | None = None) -> str:
        existing = {t.name for t in self._traces if t.trace_id != exclude_id}
        if base_name not in existing:
            return base_name
        index = 2
        while f"{base_name}_{index}" in existing:
            index += 1
        return f"{base_name}_{index}"
