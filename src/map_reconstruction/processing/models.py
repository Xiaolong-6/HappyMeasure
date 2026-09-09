"""Immutable configuration and result models for map-value processing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class BaselineMode(str, Enum):
    NONE = "none"
    MANUAL = "manual"
    MEAN = "mean"
    MEDIAN = "median"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    PERCENTILE = "percentile"


class ValueTransform(str, Enum):
    RAW = "raw"
    ABSOLUTE = "absolute"
    NEGATE = "negate"
    CUSTOM = "custom"


class NormalizationMode(str, Enum):
    NONE = "none"
    MAX_MAGNITUDE = "max_magnitude"
    MIN_MAX = "min_max"
    REFERENCE = "reference"


class ValueScale(str, Enum):
    LINEAR = "linear"
    LOG10 = "log10"


class ColorRangeMode(str, Enum):
    AUTO = "auto"
    PERCENTILE = "percentile"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class MapProcessingConfig:
    """User-selected mathematical processing, independent of display levels."""

    baseline_mode: BaselineMode = BaselineMode.NONE
    baseline_value: float | None = None
    baseline_percentile: float = 50.0
    transform: ValueTransform = ValueTransform.RAW
    custom_expression: str = "x"
    normalization: NormalizationMode = NormalizationMode.NONE
    normalization_reference: float | None = None
    value_scale: ValueScale = ValueScale.LINEAR
    color_range_mode: ColorRangeMode = ColorRangeMode.AUTO
    color_min: float | None = None
    color_max: float | None = None
    percentile_low: float = 1.0
    percentile_high: float = 99.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "baseline_mode", BaselineMode(self.baseline_mode))
        object.__setattr__(self, "transform", ValueTransform(self.transform))
        object.__setattr__(self, "normalization", NormalizationMode(self.normalization))
        object.__setattr__(self, "value_scale", ValueScale(self.value_scale))
        object.__setattr__(self, "color_range_mode", ColorRangeMode(self.color_range_mode))


@dataclass(frozen=True, slots=True)
class ProcessedMap:
    """Processed scientific values; never display-scaled or color-clipped."""

    values: np.ndarray
    baseline_used: float | None
    warnings: tuple[str, ...]
    value_label: str
    is_dimensionless: bool

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=float)
        if values.ndim != 2:
            raise ValueError("Processed map values must be a two-dimensional array.")
        values = values.copy()
        values.setflags(write=False)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "warnings", tuple(self.warnings))
