"""Deterministic, Qt-free processing pipeline for reconstructed map values."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from map_reconstruction.processing.expression import ExpressionError, evaluate_expression
from map_reconstruction.processing.models import (
    BaselineMode,
    ColorRangeMode,
    MapProcessingConfig,
    NormalizationMode,
    ProcessedMap,
    ValueScale,
    ValueTransform,
)


@dataclass(frozen=True, slots=True)
class ColorLimits:
    """Display-only levels; these never modify processed map values."""

    minimum: float
    maximum: float


def _finite(values: np.ndarray) -> np.ndarray:
    return values[np.isfinite(values)]


def _signal_label(signal_name: str) -> str:
    if signal_name == "Current_A":
        return "Current"
    if signal_name == "Voltage_V":
        return "Voltage"
    return signal_name or "Signal"


def _signal_unit(signal_name: str) -> str:
    if signal_name == "Current_A":
        return "A"
    if signal_name == "Voltage_V":
        return "V"
    return ""


def _processing_label(
    signal_name: str,
    config: MapProcessingConfig,
    is_dimensionless: bool,
) -> str:
    base = _signal_label(signal_name)
    if config.transform is ValueTransform.ABSOLUTE:
        base = f"|{base}|"
    elif config.transform is ValueTransform.NEGATE:
        base = f"-{base}"
    elif config.transform is ValueTransform.CUSTOM:
        base = "Transformed value"
    if config.normalization is not NormalizationMode.NONE:
        base = f"Normalized {base.strip('|-')}"
    if config.value_scale is ValueScale.LOG10:
        if is_dimensionless:
            return f"log10({base.lower()})"
        unit = _signal_unit(signal_name)
        return f"log10({base} / {unit})" if unit else f"log10({base})"
    if is_dimensionless:
        return base
    return base


def process_map(
    raw_values: np.ndarray,
    config: MapProcessingConfig | None = None,
    signal_name: str = "Signal",
) -> ProcessedMap:
    """Apply baseline, transform, normalization, then optional log10 in order."""

    config = config or MapProcessingConfig()
    raw = np.asarray(raw_values, dtype=float)
    if raw.ndim != 2:
        raise ValueError("Map values must be a two-dimensional array.")
    finite_raw = _finite(raw)
    warnings: list[str] = []
    dimensionless_before_log = (
        config.normalization is not NormalizationMode.NONE
        or config.transform is ValueTransform.CUSTOM
    )
    if finite_raw.size == 0:
        return ProcessedMap(
            np.full(raw.shape, np.nan, dtype=float),
            None,
            ("No finite map values are available for processing.",),
            _processing_label(signal_name, config, dimensionless_before_log),
            dimensionless_before_log or config.value_scale is ValueScale.LOG10,
        )

    baseline = 0.0
    if config.baseline_mode is BaselineMode.MANUAL:
        if config.baseline_value is None or not np.isfinite(config.baseline_value):
            raise ValueError("Manual baseline must be a finite number.")
        baseline = float(config.baseline_value)
    elif config.baseline_mode is BaselineMode.MEAN:
        baseline = float(np.mean(finite_raw))
    elif config.baseline_mode is BaselineMode.MEDIAN:
        baseline = float(np.median(finite_raw))
    elif config.baseline_mode is BaselineMode.MINIMUM:
        baseline = float(np.min(finite_raw))
    elif config.baseline_mode is BaselineMode.MAXIMUM:
        baseline = float(np.max(finite_raw))
    elif config.baseline_mode is BaselineMode.PERCENTILE:
        if not 0 <= config.baseline_percentile <= 100:
            raise ValueError("Baseline percentile must be between 0 and 100.")
        baseline = float(np.percentile(finite_raw, config.baseline_percentile))

    values = np.full(raw.shape, np.nan, dtype=float)
    valid = np.isfinite(raw)
    values[valid] = raw[valid] - baseline

    if config.transform is ValueTransform.ABSOLUTE:
        values[valid] = np.abs(values[valid])
    elif config.transform is ValueTransform.NEGATE:
        values[valid] = -values[valid]
    elif config.transform is ValueTransform.CUSTOM:
        try:
            transformed = evaluate_expression(config.custom_expression, values)
        except ExpressionError as exc:
            raise ValueError(str(exc)) from exc
        if transformed.shape not in ((), values.shape):
            raise ValueError("Custom expression returned an incompatible shape.")
        values = np.asarray(transformed + np.zeros_like(values), dtype=float)
        values[~valid] = np.nan

    finite_values = _finite(values)
    if config.normalization is NormalizationMode.MAX_MAGNITUDE:
        reference = float(np.max(np.abs(finite_values))) if finite_values.size else 0.0
        if reference == 0:
            raise ValueError("Cannot normalize by max magnitude because the reference is zero.")
        values[valid] = values[valid] / reference
    elif config.normalization is NormalizationMode.MIN_MAX:
        if finite_values.size:
            minimum, maximum = float(np.min(finite_values)), float(np.max(finite_values))
            if maximum == minimum:
                raise ValueError(
                    "Cannot apply min-max normalization because all finite values are equal."
                )
            values[valid] = (values[valid] - minimum) / (maximum - minimum)
    elif config.normalization is NormalizationMode.REFERENCE:
        reference_value = config.normalization_reference
        if reference_value is None or not np.isfinite(reference_value):
            raise ValueError("Normalization reference must be a finite number.")
        reference = float(reference_value)
        if reference == 0:
            raise ValueError("Normalization reference must be non-zero.")
        values[valid] = values[valid] / reference

    is_dimensionless = dimensionless_before_log or config.value_scale is ValueScale.LOG10
    if config.value_scale is ValueScale.LOG10:
        finite_before_log = np.isfinite(values) & (values > 0)
        excluded = int(np.count_nonzero(np.isfinite(values) & ~finite_before_log))
        with np.errstate(divide="ignore", invalid="ignore"):
            values[finite_before_log] = np.log10(values[finite_before_log])
        values[np.isfinite(values) & ~finite_before_log] = np.nan
        if excluded:
            warnings.append(f"{excluded} non-positive pixels excluded by log10 scale.")

    return ProcessedMap(
        values,
        baseline if config.baseline_mode is not BaselineMode.NONE else None,
        tuple(warnings),
        _processing_label(signal_name, config, dimensionless_before_log),
        is_dimensionless,
    )


def compute_color_limits(values: np.ndarray, config: MapProcessingConfig) -> ColorLimits | None:
    """Compute display-only levels from processed scientific values."""

    finite_values = _finite(np.asarray(values, dtype=float))
    if finite_values.size == 0:
        return None
    if config.color_range_mode is ColorRangeMode.AUTO:
        minimum, maximum = float(np.min(finite_values)), float(np.max(finite_values))
    elif config.color_range_mode is ColorRangeMode.PERCENTILE:
        if not 0 <= config.percentile_low < config.percentile_high <= 100:
            raise ValueError("Color percentiles must satisfy 0 <= low < high <= 100.")
        minimum, maximum = map(
            float,
            np.percentile(finite_values, [config.percentile_low, config.percentile_high]),
        )
    else:
        if config.color_min is None or config.color_max is None:
            raise ValueError("Manual color limits require both a minimum and maximum.")
        minimum, maximum = float(config.color_min), float(config.color_max)
        if not np.isfinite(minimum) or not np.isfinite(maximum) or minimum >= maximum:
            raise ValueError("Manual color minimum must be finite and less than maximum.")
    if minimum == maximum:
        padding = max(abs(minimum) * 0.01, 1e-12)
        return ColorLimits(minimum - padding, maximum + padding)
    return ColorLimits(minimum, maximum)
