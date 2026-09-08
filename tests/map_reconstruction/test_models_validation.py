from __future__ import annotations

import numpy as np
import pytest

from map_reconstruction.models import (
    DualOffsetParams,
    ReconstructionResult,
    TimeSeriesData,
    TimingSolution,
)


def valid_params(**overrides):
    values = {
        "rows": 2,
        "cols": 2,
        "row_a_s": 0.0,
        "row_b_s": 2.0,
        "rows_apart": 1,
        "row_offset": 0,
        "point_a_s": 0.5,
        "point_b_s": 1.5,
        "points_apart": 1,
        "point_offset": 0,
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"time_s": [[0.0, 1.0]]}, "one-dimensional"),
        ({"time_s": [0.0, float("nan")]}, "finite"),
        ({"signals": {"": [1.0, 2.0]}}, "names"),
        ({"signals": {"x": [[1.0, 2.0]]}}, "one-dimensional"),
        ({"signals": {"x": [1.0]}}, "expected"),
        ({"signals": {"x": [1.0, float("inf")]}}, "finite"),
        ({"signals": {}}, "At least one"),
    ],
)
def test_time_series_validation(kwargs, message):
    values = {"time_s": [0.0, 1.0], "signals": {"x": [1.0, 2.0]}}
    values.update(kwargs)
    with pytest.raises(ValueError, match=message):
        TimeSeriesData(**values)


def test_time_series_properties_for_single_sample():
    data = TimeSeriesData(time_s=[1.0], signals={"x": [2.0]})
    assert data.sample_count == 1
    assert data.duration_s == 0.0
    assert data.signal_names == ("x",)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"cols": 0}, "cols"),
        ({"rows_apart": 0}, "rows_apart"),
        ({"points_apart": 0}, "points_apart"),
        ({"row_a_s": float("nan")}, "anchors"),
    ],
)
def test_dual_offset_validation_covers_shape_and_anchor_guards(overrides, message):
    with pytest.raises(ValueError, match=message):
        DualOffsetParams(**valid_params(**overrides))


def test_reconstruction_result_requires_matching_two_dimensional_arrays():
    timing = TimingSolution(1.0, 0.0, 0.1, 0.0)
    with pytest.raises(ValueError, match="matching 2-D"):
        ReconstructionResult(np.zeros(2), np.zeros((1, 2)), timing)
