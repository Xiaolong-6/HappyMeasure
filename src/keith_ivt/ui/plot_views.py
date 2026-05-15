from __future__ import annotations

import math
from enum import Enum
from typing import Iterable

from keith_ivt.models import SweepMode, SweepPoint, SweepResult


class PlotView(str, Enum):
    LINEAR = "Linear"
    LOG_ABS = "Log |Y|"
    V_OVER_I = "V/I"
    DV_DI = "dV/dI"
    SIGNAL_TIME = "Signal-time"
    SPARE = "Spare"


DEFAULT_PLOT_VIEWS: tuple[PlotView, ...] = (PlotView.LINEAR, PlotView.LOG_ABS)


def safe_abs_log_values(values: Iterable[float]) -> list[float]:
    """Return absolute values suitable for log plotting; zeros become NaN."""
    out: list[float] = []
    for value in values:
        aval = abs(float(value))
        out.append(aval if aval > 0 else math.nan)
    return out


def resistance_values(result: SweepResult) -> list[float]:
    """Compute V/I point-by-point for either source mode."""
    values: list[float] = []
    for p in result.points:
        if result.config.mode is SweepMode.VOLTAGE_SOURCE:
            voltage = p.source_value
            current = p.measured_value
        else:
            current = p.source_value
            voltage = p.measured_value
        values.append(voltage / current if current != 0 else math.nan)
    return values


def differential_resistance_values(result: SweepResult) -> list[float]:
    """Compute dV/dI using local finite differences.

    The returned list has the same length as the input points. Endpoints use a
    one-sided difference; interior points use a central difference.
    """
    n = len(result.points)
    if n == 0:
        return []
    if n == 1:
        return [math.nan]

    if result.config.mode is SweepMode.VOLTAGE_SOURCE:
        voltage = [p.source_value for p in result.points]
        current = [p.measured_value for p in result.points]
    else:
        current = [p.source_value for p in result.points]
        voltage = [p.measured_value for p in result.points]

    out: list[float] = []
    for i in range(n):
        if i == 0:
            dv = voltage[1] - voltage[0]
            di = current[1] - current[0]
        elif i == n - 1:
            dv = voltage[-1] - voltage[-2]
            di = current[-1] - current[-2]
        else:
            dv = voltage[i + 1] - voltage[i - 1]
            di = current[i + 1] - current[i - 1]
        out.append(dv / di if di != 0 else math.nan)
    return out


def iv_vectors(result: SweepResult) -> tuple[list[float], list[float]]:
    """Return voltage and current vectors independent of source mode."""
    if result.config.mode is SweepMode.VOLTAGE_SOURCE:
        voltage = [p.source_value for p in result.points]
        current = [p.measured_value for p in result.points]
    else:
        voltage = [p.measured_value for p in result.points]
        current = [p.source_value for p in result.points]
    return voltage, current


def xy_for_view(result: SweepResult, view: PlotView) -> tuple[list[float], list[float], str, str, str, bool]:
    """Return x, y, xlabel, ylabel, title, y_is_log for a plot view."""
    points = result.points
    source = [p.source_value for p in points]
    measured = [p.measured_value for p in points]
    voltage, current = iv_vectors(result)

    if view is PlotView.LINEAR:
        return voltage, current, "Voltage (V)", "Current (A)", "I-V curve", False

    if view is PlotView.LOG_ABS:
        return voltage, safe_abs_log_values(current), "Voltage (V)", "|Current (A)|", "Log |I|", True

    if view is PlotView.V_OVER_I:
        return source, resistance_values(result), result.config.source_label, "V/I (Ohm)", "Static resistance V/I", False

    if view is PlotView.DV_DI:
        return source, differential_resistance_values(result), result.config.source_label, "dV/dI (Ohm)", "Differential resistance dV/dI", False

    if view is PlotView.SIGNAL_TIME:
        ylabel = result.config.measure_label
        x = [getattr(p, "elapsed_s", 0.0) for p in points]
        if not any(x):
            return list(range(1, len(points) + 1)), measured, "Point index", ylabel, "Signal vs point index", False
        return x, measured, "Elapsed time (s)", ylabel, "Signal vs time", False

    return [], [], "", "", "Spare plot", False


def layout_grid(n_views: int, arrangement: str) -> tuple[int, int]:
    """Return rows, columns for selected plot count and layout policy."""
    if n_views <= 0:
        return 1, 1
    policy = arrangement.lower().strip()
    if policy == "horizontal":
        return 1, n_views
    if policy == "vertical":
        return n_views, 1
    if n_views == 1:
        return 1, 1
    if n_views == 2:
        return 1, 2
    if n_views <= 4:
        return 2, 2
    return 2, 3
