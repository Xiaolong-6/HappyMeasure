from __future__ import annotations

import numpy as np

from map_reconstruction.methods.dual_offset import reconstruct_map, solve_timing
from map_reconstruction.models import DualOffsetParams, TimeSeriesData


def test_matlab_dual_offset_reference_parity() -> None:
    """Lock the full MATLAB dual-offset anchor, window, and aggregation contract."""

    params = DualOffsetParams(
        rows=3,
        cols=4,
        row_a_s=20.0,
        row_b_s=50.0,
        rows_apart=3,
        row_offset=2,
        point_a_s=12.5,
        point_b_s=15.5,
        points_apart=6,
        point_offset=1,
    )
    timing = solve_timing(params)
    sample_times: list[float] = []
    samples: list[float] = []
    expected = np.empty((3, 4), dtype=float)
    for row in range(params.rows):
        for column in range(params.cols):
            start = (
                timing.row_ref0_s
                + row * timing.row_period_s
                + timing.pixel1_phase_s
                + column * timing.point_period_s
            )
            value = 100.0 * row + 10.0 * column
            sample_times.extend(
                (start + 0.20 * timing.point_period_s, start + 0.30 * timing.point_period_s)
            )
            samples.extend((value + 1.0, value + 3.0))
            expected[row, column] = value + 2.0
    order = np.argsort(sample_times)
    data = TimeSeriesData(
        time_s=np.asarray(sample_times)[order],
        signals={"Current_A": np.asarray(samples)[order]},
    )

    result = reconstruct_map(data, "Current_A", params)

    assert timing.row_period_s == 10.0
    assert timing.row_ref0_s == 0.0
    assert timing.point_period_s == 0.5
    assert timing.pixel1_phase_s == 2.0
    np.testing.assert_array_equal(result.sample_counts, np.full((3, 4), 2, dtype=int))
    np.testing.assert_allclose(result.values, expected)
