from __future__ import annotations

import numpy as np
import pytest

from map_reconstruction.methods.dual_offset import MAX_RECONSTRUCTION_PIXELS, reconstruct_map
from map_reconstruction.models import DualOffsetParams, TimeSeriesData


def params(**overrides):
    values = {
        "rows": 3,
        "cols": 4,
        "row_a_s": 20.0,
        "row_b_s": 50.0,
        "rows_apart": 3,
        "row_offset": 2,
        "point_a_s": 12.5,
        "point_b_s": 15.5,
        "points_apart": 6,
        "point_offset": 1,
    }
    values.update(overrides)
    return DualOffsetParams(**values)


def test_reconstruction_recovers_known_map_from_window_samples():
    time = np.asarray(
        [2.3, 3.3, 4.3, 5.3, 12.3, 13.3, 14.3, 15.3, 22.3, 23.3, 24.3, 25.3],
        dtype=float,
    )
    expected = np.asarray([[1, 2, 3, 4], [11, 12, 13, 14], [21, 22, 23, 24]], dtype=float)
    data = TimeSeriesData(time_s=time, signals={"Current_A": expected.reshape(-1)})

    result = reconstruct_map(
        data,
        "Current_A",
        params(point_a_s=12.0, point_b_s=18.0, point_offset=0),
    )

    np.testing.assert_allclose(result.values, expected)
    np.testing.assert_array_equal(result.sample_counts, np.ones((3, 4), dtype=int))
    assert result.warnings == []


def test_empty_windows_use_nearest_sample_only_within_threshold():
    data = TimeSeriesData(time_s=np.asarray([0.0]), signals={"x": np.asarray([5.0])})
    result = reconstruct_map(
        data,
        "x",
        params(
            rows=1,
            cols=1,
            row_a_s=0.0,
            row_b_s=1.0,
            rows_apart=1,
            row_offset=0,
            point_a_s=0.1,
            point_b_s=0.2,
            points_apart=1,
            point_offset=0,
        ),
    )

    assert result.values[0, 0] == 5.0
    assert result.sample_counts[0, 0] == 1


def test_overlapping_point_train_is_a_nonfatal_warning():
    data = TimeSeriesData(time_s=np.arange(10.0), signals={"x": np.arange(10.0)})
    result = reconstruct_map(
        data,
        "x",
        params(
            rows=1,
            cols=4,
            row_a_s=0.0,
            row_b_s=1.0,
            rows_apart=1,
            row_offset=0,
            point_a_s=0.1,
            point_b_s=1.1,
            points_apart=1,
            point_offset=0,
        ),
    )

    assert "Spatial point train exceeds row period." in result.warnings


def test_reconstruction_rejects_geometry_above_responsive_ui_limit():
    data = TimeSeriesData(time_s=np.arange(10.0), signals={"x": np.arange(10.0)})

    with pytest.raises(ValueError, match="reconstruction limit"):
        reconstruct_map(
            data,
            "x",
            params(rows=1001, cols=MAX_RECONSTRUCTION_PIXELS // 1000 + 1),
        )
