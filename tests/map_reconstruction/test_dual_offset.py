from __future__ import annotations

import pytest

from map_reconstruction.methods.dual_offset import solve_timing
from map_reconstruction.models import DualOffsetParams


def make_params(**overrides):
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


def test_dual_offset_matches_specification_example():
    timing = solve_timing(make_params())

    assert timing.row_period_s == pytest.approx(10.0)
    assert timing.row_ref0_s == pytest.approx(0.0)
    assert timing.point_period_s == pytest.approx(0.5)
    assert timing.pixel1_phase_s == pytest.approx(2.0)


def test_zero_based_row_and_point_offsets_shift_phases():
    base = solve_timing(make_params())
    row_shift = solve_timing(make_params(row_offset=1))
    point_shift = solve_timing(make_params(point_offset=2))

    assert row_shift.row_ref0_s == pytest.approx(base.row_ref0_s + base.row_period_s)
    assert point_shift.pixel1_phase_s == pytest.approx(base.pixel1_phase_s - base.point_period_s)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"rows": 0}, "rows"),
        ({"row_b_s": 20.0}, "Row B"),
        ({"point_b_s": 12.5}, "Point B"),
        ({"row_offset": 3}, "row_offset"),
        ({"point_offset": 4}, "point_offset"),
    ],
)
def test_invalid_dual_offset_parameters_are_rejected(overrides, message):
    with pytest.raises(ValueError, match=message):
        solve_timing(make_params(**overrides))
