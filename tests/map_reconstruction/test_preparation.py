from __future__ import annotations

import numpy as np
import pytest

from map_reconstruction.models import TimeSeriesData
from map_reconstruction.methods.dual_offset import reconstruct_map
from map_reconstruction.models import DualOffsetParams, ScanPattern
from map_reconstruction.preparation import (
    DarkCorrectionMode,
    DarkRegion,
    ManualRegionFit,
    OutputConvention,
    PhotocurrentPolarity,
    RollingTrend,
    SignalPreparationConfig,
    prepare_signal,
)


def _data(values: list[float]) -> TimeSeriesData:
    return TimeSeriesData(np.arange(len(values), dtype=float), {"Current_A": values})


def test_none_mode_is_an_independent_identity_copy() -> None:
    data = _data([1.0, 2.0, 3.0])
    prepared = prepare_signal(data, "Current_A")
    np.testing.assert_array_equal(prepared.values, data.signals["Current_A"])
    assert prepared.baseline is None
    assert not np.shares_memory(prepared.values, data.signals["Current_A"])
    with pytest.raises(ValueError):
        prepared.values[0] = 0.0


def test_constant_dark_minus_measured_convention() -> None:
    config = SignalPreparationConfig(
        dark_correction_mode=DarkCorrectionMode.CONSTANT,
        constant_baseline=-10.0,
        output_convention=OutputConvention.DARK_MINUS_MEASURED,
    )
    prepared = prepare_signal(_data([-10.0, -12.0, -8.0]), "Current_A", config)
    np.testing.assert_allclose(prepared.values, [0.0, 2.0, -2.0])
    np.testing.assert_allclose(prepared.baseline, [-10.0] * 3)


def test_manual_regions_fit_region_medians_not_raw_sample_weights() -> None:
    data = TimeSeriesData(
        np.arange(6, dtype=float),
        {"Current_A": np.asarray([-5.0, -5.0, -5.0, -7.0, -7.0, -7.0])},
    )
    config = SignalPreparationConfig(
        dark_correction_mode=DarkCorrectionMode.MANUAL_REGIONS,
        manual_dark_regions=(DarkRegion(0.0, 1.0), DarkRegion(3.0, 5.0)),
        manual_region_fit=ManualRegionFit.LINEAR,
    )
    prepared = prepare_signal(data, "Current_A", config)
    assert prepared.baseline is not None
    np.testing.assert_allclose(prepared.baseline[0], -5.0, atol=0.6)
    np.testing.assert_allclose(prepared.baseline[5], -7.0, atol=0.6)


def test_manual_fit_requires_enough_regions() -> None:
    config = SignalPreparationConfig(
        dark_correction_mode=DarkCorrectionMode.MANUAL_REGIONS,
        manual_dark_regions=(DarkRegion(0.0, 1.0),),
        manual_region_fit=ManualRegionFit.QUADRATIC,
    )
    with pytest.raises(ValueError, match="at least 3"):
        prepare_signal(_data([1.0, 2.0, 3.0]), "Current_A", config)


def test_rolling_quantile_uses_time_bins_and_constant_edges() -> None:
    time = np.asarray([0.0, 0.2, 2.0, 2.1, 5.0])
    data = TimeSeriesData(time, {"Current_A": np.asarray([-10.0, -9.0, -8.0, -7.0, -6.0])})
    config = SignalPreparationConfig(
        dark_correction_mode=DarkCorrectionMode.ROLLING_QUANTILE,
        rolling_window_s=2.0,
        rolling_quantile=0.9,
        response_direction=PhotocurrentPolarity.NEGATIVE,
        rolling_trend=RollingTrend.PIECEWISE_LINEAR,
    )
    prepared = prepare_signal(data, "Current_A", config)
    assert prepared.baseline is not None
    assert prepared.baseline[0] == pytest.approx(-9.1)
    assert prepared.baseline[-1] == pytest.approx(-6.0)


def test_prepared_trace_can_feed_existing_reconstruction_adapter() -> None:
    data = TimeSeriesData(
        np.arange(20, dtype=float) * 0.1, {"Current_A": np.arange(20, dtype=float)}
    )
    prepared = prepare_signal(data, "Current_A")
    adapter = TimeSeriesData(prepared.time_s, {prepared.source_signal: prepared.values})
    params = DualOffsetParams(
        rows=1,
        cols=1,
        row_a_s=0.0,
        row_b_s=0.1,
        rows_apart=1,
        row_offset=0,
        point_a_s=0.0,
        point_b_s=0.1,
        points_apart=1,
        point_offset=0,
        scan_pattern=ScanPattern.SAME_DIRECTION,
    )
    result = reconstruct_map(adapter, prepared.source_signal, params)
    assert result.values.shape == (1, 1)
