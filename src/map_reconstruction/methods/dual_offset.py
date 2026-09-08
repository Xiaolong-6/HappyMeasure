from __future__ import annotations

import numpy as np

from map_reconstruction.models import (
    DualOffsetParams,
    ReconstructionResult,
    ScanPattern,
    TimeSeriesData,
    TimingSolution,
)


def solve_timing(params: DualOffsetParams) -> TimingSolution:
    """Solve row/point periods and phases from the four user anchors."""

    row_period = (params.row_b_s - params.row_a_s) / params.rows_apart
    point_period = (params.point_b_s - params.point_a_s) / params.points_apart
    if row_period <= 0:
        raise ValueError("Row B must be later than Row A for a positive row period.")
    if point_period <= 0:
        raise ValueError("Point B must be later than Point A for a positive point period.")

    row_ref0 = params.row_a_s - params.row_offset * row_period
    phase_a = (params.point_a_s - row_ref0) % row_period
    pixel1_phase = (phase_a - params.point_offset * point_period) % row_period
    return TimingSolution(
        row_period_s=float(row_period),
        row_ref0_s=float(row_ref0),
        point_period_s=float(point_period),
        pixel1_phase_s=float(pixel1_phase),
    )


def apply_scan_orientation(
    values: np.ndarray,
    sample_counts: np.ndarray,
    scan_pattern: ScanPattern,
    first_row_ltr: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply spatial orientation without changing timing mathematics."""

    oriented_values = np.asarray(values).copy()
    oriented_counts = np.asarray(sample_counts).copy()
    if scan_pattern is ScanPattern.SAME_DIRECTION:
        if not first_row_ltr:
            oriented_values = np.fliplr(oriented_values)
            oriented_counts = np.fliplr(oriented_counts)
    else:
        for row in range(oriented_values.shape[0]):
            reverse = (row % 2 == 1) if first_row_ltr else (row % 2 == 0)
            if reverse:
                oriented_values[row] = oriented_values[row, ::-1]
                oriented_counts[row] = oriented_counts[row, ::-1]
    return oriented_values, oriented_counts


def reconstruct_map(
    data: TimeSeriesData,
    signal_name: str,
    params: DualOffsetParams,
) -> ReconstructionResult:
    """Reconstruct a map using the dual-offset timing and windowed samples."""

    if signal_name not in data.signals:
        raise ValueError(f"Unknown signal {signal_name!r}.")
    if np.any(np.diff(data.time_s) < 0):
        raise ValueError("Time-series data must be sorted by time.")

    timing = solve_timing(params)
    signal = data.signals[signal_name]
    values = np.full((params.rows, params.cols), np.nan, dtype=float)
    counts = np.zeros((params.rows, params.cols), dtype=int)

    for row in range(params.rows):
        row_base = timing.row_ref0_s + row * timing.row_period_s
        for column in range(params.cols):
            pixel_start = row_base + timing.pixel1_phase_s + column * timing.point_period_s
            left = pixel_start + 0.15 * timing.point_period_s
            right = pixel_start + 0.80 * timing.point_period_s
            first = int(np.searchsorted(data.time_s, left, side="left"))
            last = int(np.searchsorted(data.time_s, right, side="right"))
            window = signal[first:last]
            if window.size:
                values[row, column] = (
                    float(np.median(window)) if params.use_median else float(np.mean(window))
                )
                counts[row, column] = int(window.size)
                continue

            center = pixel_start + 0.5 * timing.point_period_s
            nearest_index = int(np.searchsorted(data.time_s, center, side="left"))
            candidates = [
                index
                for index in (nearest_index - 1, nearest_index)
                if 0 <= index < data.time_s.size
            ]
            if candidates:
                nearest = min(candidates, key=lambda index: abs(data.time_s[index] - center))
                if abs(float(data.time_s[nearest] - center)) <= 0.30:
                    values[row, column] = float(signal[nearest])
                    counts[row, column] = 1

    oriented_values, oriented_counts = apply_scan_orientation(
        values, counts, params.scan_pattern, params.first_row_ltr
    )
    warnings: list[str] = []
    if params.cols * timing.point_period_s > timing.row_period_s:
        warnings.append("Spatial point train exceeds row period.")
    return ReconstructionResult(oriented_values, oriented_counts, timing, warnings)
