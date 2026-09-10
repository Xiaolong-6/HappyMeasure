"""Read-only value-distribution data for the optional map QC view."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

MAX_HISTOGRAM_BINS = 10_000


class HistogramRangeMode(str, Enum):
    """The display range used to bin a processed map."""

    AUTO = "auto"
    MANUAL = "manual"


class HistogramBinMode(str, Enum):
    """The supported, view-only histogram bin specifications."""

    AUTO = "auto"
    COUNT = "count"
    WIDTH = "width"


@dataclass(frozen=True, slots=True)
class HistogramConfig:
    """View-only binning choices; never a transformation of map values."""

    range_mode: HistogramRangeMode = HistogramRangeMode.AUTO
    minimum: float | None = None
    maximum: float | None = None
    bin_mode: HistogramBinMode = HistogramBinMode.AUTO
    bin_count: int = 50
    bin_width: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "range_mode", HistogramRangeMode(self.range_mode))
        object.__setattr__(self, "bin_mode", HistogramBinMode(self.bin_mode))
        if self.range_mode is HistogramRangeMode.MANUAL:
            if self.minimum is None or self.maximum is None:
                raise ValueError("Manual histogram range requires a minimum and maximum.")
            minimum, maximum = float(self.minimum), float(self.maximum)
            if not np.isfinite(minimum) or not np.isfinite(maximum) or minimum >= maximum:
                raise ValueError("Histogram minimum must be finite and less than maximum.")
            object.__setattr__(self, "minimum", minimum)
            object.__setattr__(self, "maximum", maximum)
        if self.bin_mode is HistogramBinMode.COUNT:
            count = int(self.bin_count)
            if count <= 0:
                raise ValueError("Histogram bin count must be greater than zero.")
            if count > MAX_HISTOGRAM_BINS:
                raise ValueError(f"Histogram bin count cannot exceed {MAX_HISTOGRAM_BINS:,}.")
        if self.bin_mode is HistogramBinMode.WIDTH:
            width = float(self.bin_width)
            if not np.isfinite(width) or width <= 0:
                raise ValueError("Histogram bin width must be finite and greater than zero.")
            object.__setattr__(self, "bin_width", width)


@dataclass(frozen=True, slots=True)
class HistogramData:
    """Finite reconstructed-value histogram and its compact summary."""

    counts: np.ndarray
    edges: np.ndarray
    finite_count: int
    total_count: int
    shown_count: int
    below_count: int
    above_count: int
    mean: float
    median: float
    minimum: float
    maximum: float


def _automatic_bin_count(values: np.ndarray) -> int:
    edges = np.histogram_bin_edges(values, bins="auto")
    return int(np.clip(edges.size - 1, 10, 80))


def _range_for(values: np.ndarray, config: HistogramConfig) -> tuple[float, float]:
    if config.range_mode is HistogramRangeMode.MANUAL:
        assert config.minimum is not None and config.maximum is not None
        return config.minimum, config.maximum
    minimum, maximum = float(np.min(values)), float(np.max(values))
    if minimum == maximum:
        padding = max(abs(minimum) * 0.01, 0.5)
        return minimum - padding, maximum + padding
    return minimum, maximum


def _edges(
    values: np.ndarray, minimum: float, maximum: float, config: HistogramConfig
) -> np.ndarray:
    if config.bin_mode is HistogramBinMode.AUTO:
        return np.linspace(minimum, maximum, _automatic_bin_count(values) + 1)
    if config.bin_mode is HistogramBinMode.COUNT:
        return np.linspace(minimum, maximum, int(config.bin_count) + 1)
    bin_count = max(1, int(np.ceil((maximum - minimum) / config.bin_width)))
    if bin_count > MAX_HISTOGRAM_BINS:
        raise ValueError(
            f"Histogram bin width would create {bin_count:,} bins; "
            f"the maximum is {MAX_HISTOGRAM_BINS:,}."
        )
    edges = minimum + np.arange(bin_count + 1, dtype=float) * config.bin_width
    edges[-1] = maximum
    return edges


def make_histogram_data(
    values: np.ndarray, config: HistogramConfig | None = None
) -> HistogramData | None:
    """Return a constrained, read-only histogram of finite scientific values.

    NumPy histogram semantics apply in all modes: left edges are inclusive and
    the final right edge is included. Manual range exclusions are reported
    rather than silently changing the global mean or median.
    """

    source = np.asarray(values, dtype=float)
    finite_values = source[np.isfinite(source)]
    if finite_values.size == 0:
        return None

    current = config or HistogramConfig()
    minimum, maximum = _range_for(finite_values, current)
    below = int(np.count_nonzero(finite_values < minimum))
    above = int(np.count_nonzero(finite_values > maximum))
    shown = finite_values[(finite_values >= minimum) & (finite_values <= maximum)]
    counts, edges = np.histogram(shown, bins=_edges(finite_values, minimum, maximum, current))
    return HistogramData(
        counts=counts,
        edges=edges,
        finite_count=int(finite_values.size),
        total_count=int(source.size),
        shown_count=int(shown.size),
        below_count=below,
        above_count=above,
        mean=float(np.mean(finite_values)),
        median=float(np.median(finite_values)),
        minimum=minimum,
        maximum=maximum,
    )
