from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from keith_ivt.drivers.base import MeasureMode, SourceMode
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, make_constant_time_values, make_source_values, minimum_interval_seconds, validate_config
from keith_ivt.core.adaptive_logic import adaptive_values_from_logic


class SweepExecutionKind(str, Enum):
    STEP = "STEP"
    CONSTANT_TIME = "CONSTANT_TIME"
    ADAPTIVE = "ADAPTIVE"
    MANUAL_OUTPUT = "MANUAL_OUTPUT"


@dataclass(frozen=True)
class SweepPlan:
    """Driver-neutral execution plan.

    UI panels and future IV/CV workflows should produce this object before any
    hardware output is enabled. It contains no Tk state and no serial code.
    """

    source_mode: SourceMode
    measure_mode: MeasureMode
    values: tuple[float, ...]
    compliance: float
    nplc: float
    execution_kind: SweepExecutionKind
    interval_s: float | None = None
    autorange: bool = True
    source_range: float | None = None
    measure_range: float | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def point_count(self) -> int:
        return len(self.values)

    @property
    def estimated_seconds(self) -> float:
        base = minimum_interval_seconds(self.nplc)
        if self.execution_kind is SweepExecutionKind.CONSTANT_TIME and self.interval_s is not None:
            return self.point_count * max(self.interval_s, base)
        return self.point_count * base


def source_measure_from_legacy_mode(mode: SweepMode) -> tuple[SourceMode, MeasureMode]:
    if mode is SweepMode.VOLTAGE_SOURCE:
        return SourceMode.VOLTAGE, MeasureMode.CURRENT
    return SourceMode.CURRENT, MeasureMode.VOLTAGE


def plan_from_config(config: SweepConfig) -> SweepPlan:
    """Build a new driver-neutral plan from the legacy SweepConfig.

    This keeps the existing UI working while future panels can bypass SweepConfig
    and construct SweepPlan directly.
    """
    validate_config(config)
    source_mode, measure_mode = source_measure_from_legacy_mode(config.mode)
    warnings: list[str] = []
    if config.sweep_kind is SweepKind.MANUAL_OUTPUT:
        values: tuple[float, ...] = ()
        kind = SweepExecutionKind.MANUAL_OUTPUT
        warnings.append("Manual output requires UI safety interlock and is not a normal sweep.")
    elif config.sweep_kind is SweepKind.CONSTANT_TIME:
        values = tuple(make_constant_time_values(config.constant_value, config.duration_s, config.interval_s))
        kind = SweepExecutionKind.CONSTANT_TIME
    elif config.sweep_kind is SweepKind.ADAPTIVE:
        values = tuple(adaptive_values_from_logic(config.adaptive_logic))
        kind = SweepExecutionKind.ADAPTIVE
    else:
        values = tuple(make_source_values(config.start, config.stop, config.step))
        kind = SweepExecutionKind.STEP
    return SweepPlan(
        source_mode=source_mode,
        measure_mode=measure_mode,
        values=values,
        compliance=config.compliance,
        nplc=config.nplc,
        execution_kind=kind,
        interval_s=config.interval_s if config.sweep_kind is SweepKind.CONSTANT_TIME else None,
        autorange=config.autorange,
        source_range=None if config.autorange else config.source_range,
        measure_range=None if config.autorange else config.measure_range,
        metadata={
            "device_name": config.device_name,
            "operator": config.operator,
            "legacy_mode": config.mode.value,
            "legacy_sweep_kind": config.sweep_kind.value,
        },
        warnings=tuple(warnings),
    )


def make_plan(
    *,
    source_mode: SourceMode,
    measure_mode: MeasureMode,
    values: Iterable[float],
    compliance: float,
    nplc: float,
    execution_kind: SweepExecutionKind = SweepExecutionKind.STEP,
    interval_s: float | None = None,
    autorange: bool = True,
    source_range: float | None = None,
    measure_range: float | None = None,
    metadata: dict[str, str] | None = None,
) -> SweepPlan:
    vals = tuple(float(v) for v in values)
    if execution_kind is not SweepExecutionKind.MANUAL_OUTPUT and not vals:
        raise ValueError("SweepPlan values cannot be empty for a normal sweep.")
    if compliance <= 0:
        raise ValueError("Compliance must be positive.")
    if nplc <= 0:
        raise ValueError("NPLC must be positive.")
    if not autorange:
        if source_range is None or source_range <= 0 or measure_range is None or measure_range <= 0:
            raise ValueError("Fixed source_range and measure_range are required when autorange is disabled.")
    return SweepPlan(
        source_mode=source_mode,
        measure_mode=measure_mode,
        values=vals,
        compliance=float(compliance),
        nplc=float(nplc),
        execution_kind=execution_kind,
        interval_s=interval_s,
        autorange=autorange,
        source_range=source_range,
        measure_range=measure_range,
        metadata=metadata or {},
    )
