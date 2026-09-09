"""Read-only value-distribution data for the optional map QC view."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class HistogramData:
    """Finite reconstructed-value histogram and its compact summary."""

    counts: np.ndarray
    edges: np.ndarray
    finite_count: int
    total_count: int
    mean: float
    median: float


def make_histogram_data(values: np.ndarray) -> HistogramData | None:
    """Return a constrained automatic histogram of finite scientific map values."""

    source = np.asarray(values, dtype=float)
    finite_values = source[np.isfinite(source)]
    if finite_values.size == 0:
        return None

    auto_edges = np.histogram_bin_edges(finite_values, bins="auto")
    bin_count = int(np.clip(auto_edges.size - 1, 10, 80))
    counts, edges = np.histogram(finite_values, bins=bin_count)
    return HistogramData(
        counts=counts,
        edges=edges,
        finite_count=int(finite_values.size),
        total_count=int(source.size),
        mean=float(np.mean(finite_values)),
        median=float(np.median(finite_values)),
    )
