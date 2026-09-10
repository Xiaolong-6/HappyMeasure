"""Explicit phase-window reconstruction for asynchronous raster traces.

The period anchors determine only periods.  Row origin, acquisition-window
position, and acquisition-window width are independent scientific parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from map_reconstruction.methods.dual_offset import MAX_RECONSTRUCTION_PIXELS, apply_scan_orientation
from map_reconstruction.models import (
    Aggregation,
    DualOffsetParams,
    PhaseWindowParams,
    PhaseWindowTimingSolution,
    ReconstructionResult,
    TimeSeriesData,
    WindowMode,
)

WINDOW_LEFT_FRACTION = 0.15
WINDOW_RIGHT_FRACTION = 0.80
LEGACY_WINDOW_CENTER_FRACTION = (WINDOW_LEFT_FRACTION + WINDOW_RIGHT_FRACTION) / 2


@dataclass(frozen=True, slots=True)
class PhaseWindowConversion:
    """Pure, canonical conversion of Legacy Dual Offset parameters."""

    params: PhaseWindowParams
    timing: PhaseWindowTimingSolution


def solve_phase_window_timing(params: PhaseWindowParams) -> PhaseWindowTimingSolution:
    """Derive independent period, origin, center phase, and window width."""

    row_period = (params.row_b_s - params.row_a_s) / params.rows_apart
    point_period = (params.point_b_s - params.point_a_s) / params.points_apart
    if row_period <= 0:
        raise ValueError("Row B must be later than Row A for a positive row period.")
    if point_period <= 0:
        raise ValueError("Point B must be later than Point A for a positive point period.")
    if params.window_mode is WindowMode.FRACTION:
        window_width = params.window_fraction * point_period
    else:
        if params.window_duration_s is None:  # guarded by PhaseWindowParams validation
            raise ValueError("Fixed-duration windows require a window duration.")
        window_width = params.window_duration_s
    if window_width > point_period:
        raise ValueError("Acquisition window width must not exceed the point period.")
    row0 = params.row_a_s - (params.row_offset + params.y_phase_fraction) * row_period
    center_phase = (params.x_period_offset + params.x_phase_fraction) * point_period
    first_start = center_phase - window_width / 2
    last_end = center_phase + (params.cols - 1) * point_period + window_width / 2
    if first_start < -np.finfo(float).eps * max(1.0, row_period):
        raise ValueError("The first acquisition window precedes its row boundary.")
    if last_end > row_period + np.finfo(float).eps * max(1.0, row_period):
        raise ValueError("Mapped acquisition windows exceed one row period.")
    return PhaseWindowTimingSolution(
        row_period_s=float(row_period),
        point_period_s=float(point_period),
        row0_s=float(row0),
        first_window_center_phase_s=float(center_phase),
        window_width_s=float(window_width),
    )


def window_centers(timing: PhaseWindowTimingSolution, rows: int, cols: int) -> np.ndarray:
    """Return physical window centers, shaped ``(rows, cols)``."""

    row_bases = timing.row0_s + np.arange(rows, dtype=float)[:, None] * timing.row_period_s
    column_phases = (
        timing.first_window_center_phase_s
        + np.arange(cols, dtype=float)[None, :] * timing.point_period_s
    )
    return row_bases + column_phases


def window_bounds(timing: PhaseWindowTimingSolution, rows: int, cols: int) -> np.ndarray:
    """Return ``[start, end)`` bounds for every map pixel."""

    centers = window_centers(timing, rows, cols)
    half_width = timing.window_width_s / 2
    return np.stack((centers - half_width, centers + half_width), axis=-1)


def effective_window_bounds(
    params: PhaseWindowParams, timing: PhaseWindowTimingSolution
) -> np.ndarray:
    """Return the canonical ``[start, end)`` bounds used by the core."""

    return window_bounds(timing, params.rows, params.cols)


def reconstruct_phase_window_map(
    data: TimeSeriesData, signal_name: str, params: PhaseWindowParams
) -> ReconstructionResult:
    """Aggregate all raw samples in each explicit ``[start, end)`` window."""

    if signal_name not in data.signals:
        raise ValueError(f"Unknown signal {signal_name!r}.")
    if np.any(np.diff(data.time_s) < 0):
        raise ValueError("Time-series data must be sorted by time.")
    if params.rows * params.cols > MAX_RECONSTRUCTION_PIXELS:
        raise ValueError(
            f"Map size exceeds the {MAX_RECONSTRUCTION_PIXELS:,}-pixel reconstruction limit."
        )
    timing = solve_phase_window_timing(params)
    bounds = effective_window_bounds(params, timing)
    signal = data.signals[signal_name]
    values = np.full((params.rows, params.cols), np.nan, dtype=float)
    counts = np.zeros((params.rows, params.cols), dtype=int)
    for row in range(params.rows):
        for column in range(params.cols):
            left, right = bounds[row, column]
            first = int(np.searchsorted(data.time_s, left, side="left"))
            last = int(np.searchsorted(data.time_s, right, side="left"))
            samples = signal[first:last]
            counts[row, column] = samples.size
            if samples.size:
                values[row, column] = (
                    float(np.median(samples))
                    if params.aggregation is Aggregation.MEDIAN
                    else float(np.mean(samples))
                )
    oriented_values, oriented_counts = apply_scan_orientation(
        values, counts, params.scan_pattern, params.first_row_ltr
    )
    return ReconstructionResult(oriented_values, oriented_counts, timing, [])


def convert_legacy_to_phase_window(params: DualOffsetParams) -> PhaseWindowConversion:
    """Convert Legacy windows exactly into canonical Phase Window parameters.

    Legacy's first sample window is ``[pixel_start + .15*Tpoint,
    pixel_start + .80*Tpoint]``; its center is therefore ``.475*Tpoint``
    after ``pixel_start``.  The resulting point-period coordinate is split
    using ``floor`` so the stored fractional phase is always in ``[0, 1)``.
    """

    from map_reconstruction.methods.dual_offset import solve_timing

    legacy = solve_timing(params)
    coordinate = (
        legacy.pixel1_phase_s + LEGACY_WINDOW_CENTER_FRACTION * legacy.point_period_s
    ) / legacy.point_period_s
    x_offset = int(np.floor(coordinate + 1e-12))
    x_phase = float(coordinate - x_offset)
    converted = PhaseWindowParams(
        rows=params.rows,
        cols=params.cols,
        row_a_s=params.row_a_s,
        row_b_s=params.row_b_s,
        rows_apart=params.rows_apart,
        row_offset=params.row_offset,
        y_phase_fraction=0.0,
        point_a_s=params.point_a_s,
        point_b_s=params.point_b_s,
        points_apart=params.points_apart,
        x_period_offset=x_offset,
        x_phase_fraction=x_phase,
        window_mode=WindowMode.FRACTION,
        window_fraction=WINDOW_RIGHT_FRACTION - WINDOW_LEFT_FRACTION,
        scan_pattern=params.scan_pattern,
        first_row_ltr=params.first_row_ltr,
        aggregation=Aggregation.MEDIAN if params.use_median else Aggregation.MEAN,
    )
    timing = solve_phase_window_timing(converted)
    return PhaseWindowConversion(converted, timing)
