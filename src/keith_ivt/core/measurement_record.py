from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from keith_ivt.models import SweepResult


@dataclass
class TraceRecord:
    result: SweepResult
    name: str
    visible: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def point_count(self) -> int:
        return len(self.result.points)


@dataclass
class MeasurementSession:
    traces: list[TraceRecord] = field(default_factory=list)

    def add_result(self, result: SweepResult, name: str | None = None) -> TraceRecord:
        record = TraceRecord(result=result, name=name or result.config.device_name or f"Trace_{len(self.traces) + 1}")
        self.traces.append(record)
        return record

    def clear(self) -> None:
        self.traces.clear()

    def visible_results(self) -> list[SweepResult]:
        return [trace.result for trace in self.traces if trace.visible]

    def extend(self, records: Iterable[TraceRecord]) -> None:
        self.traces.extend(records)
