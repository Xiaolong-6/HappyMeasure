from __future__ import annotations

import numpy as np
import pytest

from map_reconstruction.methods.dual_offset import reconstruct_map
from map_reconstruction.methods.phase_window import (
    convert_legacy_to_phase_window,
    reconstruct_phase_window_map,
    solve_phase_window_timing,
    window_bounds,
    window_centers,
)
from map_reconstruction.models import (
    Aggregation,
    DualOffsetParams,
    PhaseWindowParams,
    ScanPattern,
    TimeSeriesData,
    WindowMode,
)


def _params(**changes: object) -> PhaseWindowParams:
    values: dict[str, object] = dict(
        rows=2,
        cols=4,
        row_a_s=10.0,
        row_b_s=30.0,
        rows_apart=2,
        row_offset=0,
        y_phase_fraction=0.25,
        point_a_s=1.0,
        point_b_s=4.0,
        points_apart=3,
        x_period_offset=1,
        x_phase_fraction=0.5,
        window_mode=WindowMode.FRACTION,
        window_fraction=0.5,
    )
    values.update(changes)
    return PhaseWindowParams(**values)


def _data() -> TimeSeriesData:
    time = np.arange(0.0, 30.0, 0.1) + 0.013
    return TimeSeriesData(time, {"Current_A": time.copy()})


def test_phase_window_solves_independent_period_phase_and_bounds() -> None:
    timing = solve_phase_window_timing(_params())

    assert timing.row_period_s == pytest.approx(10.0)
    assert timing.point_period_s == pytest.approx(1.0)
    assert timing.row0_s == pytest.approx(7.5)
    assert timing.first_window_center_phase_s == pytest.approx(1.5)
    assert timing.window_width_s == pytest.approx(0.5)
    np.testing.assert_allclose(window_centers(timing, 2, 2), [[9.0, 10.0], [19.0, 20.0]])
    np.testing.assert_allclose(window_bounds(timing, 1, 2), [[[8.75, 9.25], [9.75, 10.25]]])


def test_phase_window_uses_start_inclusive_end_exclusive_samples() -> None:
    params = _params(rows=1, cols=1, row_a_s=0.0, row_b_s=10.0, rows_apart=1, y_phase_fraction=0.0)
    data = TimeSeriesData(np.asarray([1.25, 1.5, 1.75]), {"Current_A": np.asarray([1.0, 2.0, 3.0])})

    result = reconstruct_phase_window_map(data, "Current_A", params)

    assert result.sample_counts[0, 0] == 2
    assert result.values[0, 0] == pytest.approx(1.5)


def test_phase_window_fixed_duration_empty_window_and_mean() -> None:
    params = _params(
        rows=1,
        cols=2,
        row_a_s=0.0,
        row_b_s=10.0,
        rows_apart=1,
        y_phase_fraction=0.0,
        window_mode=WindowMode.FIXED_DURATION,
        window_duration_s=0.2,
        aggregation=Aggregation.MEAN,
    )
    data = TimeSeriesData(np.asarray([1.45, 1.55, 3.4]), {"Current_A": np.asarray([1.0, 3.0, 5.0])})

    result = reconstruct_phase_window_map(data, "Current_A", params)

    assert result.sample_counts.tolist() == [[2, 0]]
    assert result.values[0, 0] == pytest.approx(2.0)
    assert np.isnan(result.values[0, 1])


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"window_fraction": 1.1}, "at most one"),
        ({"window_mode": WindowMode.FIXED_DURATION, "window_duration_s": 1.1}, "must not exceed"),
        ({"x_period_offset": 9}, "exceed one row"),
    ],
)
def test_phase_window_rejects_invalid_window_geometry(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        solve_phase_window_timing(_params(**changes))


def test_phase_canonicalization_and_scan_orientation() -> None:
    params = _params(y_phase_fraction=1.25, x_phase_fraction=-0.5, rows=1, cols=2)
    assert params.y_phase_fraction == pytest.approx(0.25)
    assert params.x_phase_fraction == pytest.approx(0.5)
    data = _data()
    params.first_row_ltr = False
    result = reconstruct_phase_window_map(data, "Current_A", params)
    assert result.values[0, 0] > result.values[0, 1]


@pytest.mark.parametrize(
    "scan_pattern, first_row_ltr",
    [
        (ScanPattern.SAME_DIRECTION, True),
        (ScanPattern.SAME_DIRECTION, False),
        (ScanPattern.SERPENTINE, True),
        (ScanPattern.SERPENTINE, False),
    ],
)
def test_legacy_conversion_reproduces_legacy_windows_and_values(
    scan_pattern: ScanPattern, first_row_ltr: bool
) -> None:
    legacy_params = DualOffsetParams(
        rows=2,
        cols=4,
        row_a_s=10.0,
        row_b_s=30.0,
        rows_apart=2,
        row_offset=0,
        point_a_s=2.0,
        point_b_s=5.0,
        points_apart=3,
        point_offset=0,
        scan_pattern=scan_pattern,
        first_row_ltr=first_row_ltr,
    )
    data = _data()

    converted = convert_legacy_to_phase_window(legacy_params)
    legacy = reconstruct_map(data, "Current_A", legacy_params)
    phase_window = reconstruct_phase_window_map(data, "Current_A", converted.params)

    np.testing.assert_allclose(phase_window.values, legacy.values, equal_nan=True)
    np.testing.assert_array_equal(phase_window.sample_counts, legacy.sample_counts)
    assert converted.timing.window_width_s == pytest.approx(0.65)
