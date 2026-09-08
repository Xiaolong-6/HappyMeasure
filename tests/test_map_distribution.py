import numpy as np

from map_reconstruction.ui.distribution import make_histogram_data


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
