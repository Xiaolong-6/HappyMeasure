from __future__ import annotations

import numpy as np
import pytest

from map_reconstruction.processing import (
    BaselineMode,
    ColorRangeMode,
    MapProcessingConfig,
    NormalizationMode,
    ValueScale,
    ValueTransform,
    compute_color_limits,
    process_map,
)
from map_reconstruction.processing.expression import ExpressionError, evaluate_expression


def test_raw_processing_is_identity_and_does_not_mutate_source() -> None:
    raw = np.asarray([[-2e-4, -1e-4], [-5e-5, np.nan]])
    original = raw.copy()
    processed = process_map(raw, signal_name="Current_A")

    np.testing.assert_allclose(processed.values, raw, equal_nan=True)
    np.testing.assert_allclose(raw, original, equal_nan=True)
    assert processed.baseline_used is None
    assert not processed.is_dimensionless


def test_absolute_and_negate_preserve_nan() -> None:
    raw = np.asarray([[-2.0, 1.0, np.nan]])
    absolute = process_map(raw, MapProcessingConfig(transform=ValueTransform.ABSOLUTE))
    negate = process_map(raw, MapProcessingConfig(transform=ValueTransform.NEGATE))

    np.testing.assert_allclose(absolute.values[0, :2], [2.0, 1.0])
    np.testing.assert_allclose(negate.values[0, :2], [2.0, -1.0])
    assert np.isnan(absolute.values[0, 2])
    assert np.isnan(negate.values[0, 2])


def test_baseline_is_applied_before_absolute_transform() -> None:
    raw = np.asarray([[-12.0, -8.0]])
    config = MapProcessingConfig(
        baseline_mode=BaselineMode.MANUAL,
        baseline_value=-10.0,
        transform=ValueTransform.ABSOLUTE,
    )
    processed = process_map(raw, config)

    np.testing.assert_allclose(processed.values, [[2.0, 2.0]])
    assert processed.baseline_used == -10.0


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (BaselineMode.MEAN, 2.0),
        (BaselineMode.MEDIAN, 2.0),
        (BaselineMode.MINIMUM, 1.0),
        (BaselineMode.MAXIMUM, 3.0),
        (BaselineMode.PERCENTILE, 2.0),
    ],
)
def test_statistical_baselines(mode: BaselineMode, expected: float) -> None:
    processed = process_map(
        np.asarray([[1.0, 2.0, 3.0]]),
        MapProcessingConfig(baseline_mode=mode, baseline_percentile=50.0),
    )

    assert processed.baseline_used == expected


def test_custom_processing_marks_values_as_transformed_and_supports_broadcasting() -> None:
    processed = process_map(
        np.asarray([[-2.0, 1.0]]),
        MapProcessingConfig(transform=ValueTransform.CUSTOM, custom_expression="x * 2 + 1"),
        signal_name="Current_A",
    )

    np.testing.assert_allclose(processed.values, [[-3.0, 3.0]])
    assert processed.is_dimensionless
    assert processed.value_label == "Transformed value"


def test_reference_normalization_and_degenerate_min_max_warning() -> None:
    reference = process_map(
        np.asarray([[-4.0, 2.0]]),
        MapProcessingConfig(
            normalization=NormalizationMode.REFERENCE,
            normalization_reference=2.0,
        ),
    )
    np.testing.assert_allclose(reference.values, [[-2.0, 1.0]])
    assert reference.is_dimensionless
    with pytest.raises(ValueError, match="all finite values are equal"):
        process_map(
            np.asarray([[4.0, 4.0]]),
            MapProcessingConfig(normalization=NormalizationMode.MIN_MAX),
        )


def test_empty_map_and_invalid_processing_inputs_are_explicit() -> None:
    empty = process_map(np.full((1, 2), np.nan))
    assert np.isnan(empty.values).all()
    with pytest.raises(ValueError, match="two-dimensional"):
        process_map(np.asarray([1.0, 2.0]))
    with pytest.raises(ValueError, match="percentile"):
        process_map(
            np.asarray([[1.0, 2.0]]),
            MapProcessingConfig(baseline_mode=BaselineMode.PERCENTILE, baseline_percentile=101.0),
        )


def test_normalization_modes_and_zero_protection() -> None:
    max_magnitude = process_map(
        np.asarray([[-4.0, 2.0]]),
        MapProcessingConfig(normalization=NormalizationMode.MAX_MAGNITUDE),
    )
    min_max = process_map(
        np.asarray([[2.0, 4.0, 6.0]]),
        MapProcessingConfig(normalization=NormalizationMode.MIN_MAX),
    )
    np.testing.assert_allclose(max_magnitude.values, [[-1.0, 0.5]])
    np.testing.assert_allclose(min_max.values, [[0.0, 0.5, 1.0]])

    with pytest.raises(ValueError, match="max magnitude"):
        process_map(
            np.zeros((1, 2)),
            MapProcessingConfig(normalization=NormalizationMode.MAX_MAGNITUDE),
        )


def test_log10_rejects_non_positive_values_without_epsilon() -> None:
    processed = process_map(
        np.asarray([[100.0, 10.0, 1.0, 0.0, -1.0]]),
        MapProcessingConfig(value_scale=ValueScale.LOG10),
    )

    np.testing.assert_allclose(processed.values[0, :3], [2.0, 1.0, 0.0])
    assert np.isnan(processed.values[0, 3:]).all()
    assert "2 non-positive" in processed.warnings[0]


def test_log10_physical_and_dimensionless_labels_are_explicit() -> None:
    current = process_map(
        np.asarray([[1e-6]]),
        MapProcessingConfig(value_scale=ValueScale.LOG10),
        signal_name="Current_A",
    )
    voltage = process_map(
        np.asarray([[1.0]]),
        MapProcessingConfig(value_scale=ValueScale.LOG10),
        signal_name="Voltage_V",
    )
    normalized = process_map(
        np.asarray([[1.0]]),
        MapProcessingConfig(
            normalization=NormalizationMode.MAX_MAGNITUDE,
            value_scale=ValueScale.LOG10,
        ),
        signal_name="Current_A",
    )

    assert "Current / A" in current.value_label
    assert "Voltage / V" in voltage.value_label
    assert "A" not in normalized.value_label


def test_color_limits_do_not_change_processed_values() -> None:
    values = np.asarray([[-10.0, -2.0, 1.0, 10.0]])
    config = MapProcessingConfig(color_range_mode=ColorRangeMode.PERCENTILE)
    processed = process_map(values, config)
    before = processed.values.copy()
    limits = compute_color_limits(processed.values, config)

    assert limits is not None
    np.testing.assert_array_equal(processed.values, before)
    assert limits.minimum < limits.maximum


def test_manual_and_degenerate_color_limits() -> None:
    manual = compute_color_limits(
        np.asarray([[1.0, 2.0]]),
        MapProcessingConfig(
            color_range_mode=ColorRangeMode.MANUAL,
            color_min=1.0,
            color_max=2.0,
        ),
    )
    constant = compute_color_limits(np.asarray([[2.0, 2.0]]), MapProcessingConfig())

    assert manual is not None and (manual.minimum, manual.maximum) == (1.0, 2.0)
    assert constant is not None and constant.minimum < 2.0 < constant.maximum
    assert compute_color_limits(np.full((1, 1), np.nan), MapProcessingConfig()) is None


def test_invalid_color_percentiles_are_rejected() -> None:
    with pytest.raises(ValueError, match="Color percentiles"):
        compute_color_limits(
            np.asarray([[1.0, 2.0]]),
            MapProcessingConfig(
                color_range_mode=ColorRangeMode.PERCENTILE,
                percentile_low=90.0,
                percentile_high=10.0,
            ),
        )


def test_custom_expression_is_restricted_and_supports_math_functions() -> None:
    x = np.asarray([[-2.0, 1.0]])
    np.testing.assert_allclose(evaluate_expression("abs(x) * 2", x), [[4.0, 2.0]])
    np.testing.assert_allclose(evaluate_expression("clip(x, -1, 1)", x), [[-1.0, 1.0]])
    for expression in (
        '__import__("os")',
        'open("file")',
        "x.__class__",
        "().__class__",
        "lambda x: x",
        "[v for v in x]",
        "1 / 0",
    ):
        with pytest.raises(ExpressionError):
            evaluate_expression(expression, x)

    np.testing.assert_allclose(evaluate_expression("x - 1", x), [[-3.0, 0.0]])
    np.testing.assert_allclose(evaluate_expression("x / 2", x), [[-1.0, 0.5]])
    np.testing.assert_allclose(evaluate_expression("x ** 2", x), [[4.0, 1.0]])
    for expression in ("unknown(x)", "abs(x, 1)", "x[0]", "True"):
        with pytest.raises(ExpressionError):
            evaluate_expression(expression, x)


def test_invalid_manual_color_range_is_rejected() -> None:
    values = np.asarray([[1.0, 2.0]])
    with pytest.raises(ValueError, match="less than maximum"):
        compute_color_limits(
            values,
            MapProcessingConfig(
                color_range_mode=ColorRangeMode.MANUAL,
                color_min=3.0,
                color_max=3.0,
            ),
        )


def test_zero_reference_normalization_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-zero"):
        process_map(
            np.asarray([[1.0, 2.0]]),
            MapProcessingConfig(
                normalization=NormalizationMode.REFERENCE,
                normalization_reference=0.0,
            ),
        )
