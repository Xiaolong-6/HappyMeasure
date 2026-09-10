import numpy as np

import pytest

from map_reconstruction.qc.distribution import (
    HistogramBinMode,
    HistogramConfig,
    HistogramRangeMode,
    MAX_HISTOGRAM_BINS,
    make_histogram_data,
)


def test_histogram_uses_only_finite_scientific_map_values() -> None:
    values = np.array([[1.0, np.nan, 3.0], [np.inf, 5.0, -np.inf]])

    histogram = make_histogram_data(values)

    assert histogram is not None
    assert histogram.finite_count == 3
    assert histogram.total_count == 6
    assert int(histogram.counts.sum()) == 3
    assert histogram.mean == 3.0
    assert histogram.median == 3.0
    assert 10 <= histogram.counts.size <= 80


def test_histogram_empty_state_has_no_default_axes_data() -> None:
    assert make_histogram_data(np.full((3, 4), np.nan)) is None


def test_histogram_distribution_is_independent_of_display_orientation() -> None:
    values = np.array([[1.0, 2.0, np.nan], [4.0, 8.0, 16.0]])

    original = make_histogram_data(values)
    flipped = make_histogram_data(np.flipud(values))

    assert original is not None
    assert flipped is not None
    assert np.array_equal(original.counts, flipped.counts)
    assert np.array_equal(original.edges, flipped.edges)
    assert original.mean == flipped.mean
    assert original.median == flipped.median


def test_histogram_manual_range_reports_exclusions_without_mutating_statistics() -> None:
    values = np.array([0.0, 1.0, 2.0, 3.0, np.nan])
    histogram = make_histogram_data(
        values,
        HistogramConfig(
            range_mode=HistogramRangeMode.MANUAL,
            minimum=1.0,
            maximum=2.0,
            bin_mode=HistogramBinMode.COUNT,
            bin_count=2,
        ),
    )
    assert histogram is not None
    assert histogram.shown_count == 2
    assert histogram.below_count == 1
    assert histogram.above_count == 1
    assert histogram.counts.sum() == 2
    assert histogram.mean == pytest.approx(1.5)
    assert histogram.median == pytest.approx(1.5)


def test_histogram_count_and_width_modes_include_rightmost_edge() -> None:
    values = np.array([0.0, 0.5, 1.0])
    count = make_histogram_data(
        values, HistogramConfig(bin_mode=HistogramBinMode.COUNT, bin_count=2)
    )
    width = make_histogram_data(
        values, HistogramConfig(bin_mode=HistogramBinMode.WIDTH, bin_width=0.4)
    )
    assert count is not None and width is not None
    assert count.counts.sum() == 3
    assert width.counts.sum() == 3
    assert width.edges[-1] == pytest.approx(1.0)


@pytest.mark.parametrize(
    "kwargs",
    (
        {"range_mode": HistogramRangeMode.MANUAL, "minimum": 1.0, "maximum": 1.0},
        {"bin_mode": HistogramBinMode.COUNT, "bin_count": 0},
        {"bin_mode": HistogramBinMode.WIDTH, "bin_width": 0.0},
    ),
)
def test_histogram_rejects_invalid_view_only_config(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        HistogramConfig(**kwargs)


def test_histogram_rejects_excessive_explicit_bin_count() -> None:
    with pytest.raises(ValueError, match=f"{MAX_HISTOGRAM_BINS:,}"):
        HistogramConfig(bin_mode=HistogramBinMode.COUNT, bin_count=MAX_HISTOGRAM_BINS + 1)


def test_histogram_rejects_excessive_width_derived_bin_count() -> None:
    config = HistogramConfig(bin_mode=HistogramBinMode.WIDTH, bin_width=1e-9)
    with pytest.raises(ValueError, match="maximum"):
        make_histogram_data(np.array([0.0, 1.0]), config)
