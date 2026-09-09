from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(slots=True)
class TimeSeriesData:
    """Generic, sorted time-series data for reconstruction methods."""

    time_s: np.ndarray
    signals: dict[str, np.ndarray]
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None

    def __post_init__(self) -> None:
        self.time_s = np.asarray(self.time_s, dtype=float)
        if self.time_s.ndim != 1:
            raise ValueError("time_s must be a one-dimensional array.")
        if not np.all(np.isfinite(self.time_s)):
            raise ValueError("time_s must contain only finite values.")

        expected_length = self.time_s.size
        normalized: dict[str, np.ndarray] = {}
        for name, values in self.signals.items():
            if not str(name).strip():
                raise ValueError("Signal names must not be empty.")
            array = np.asarray(values, dtype=float)
            if array.ndim != 1:
                raise ValueError(f"Signal {name!r} must be one-dimensional.")
            if array.size != expected_length:
                raise ValueError(
                    f"Signal {name!r} has {array.size} samples; expected {expected_length}."
                )
            if not np.all(np.isfinite(array)):
                raise ValueError(f"Signal {name!r} must contain only finite values.")
            normalized[str(name)] = array

        if not normalized:
            raise ValueError("At least one signal is required.")
        self.signals = normalized
        self.metadata = dict(self.metadata)
        if self.source_path is not None:
            self.source_path = Path(self.source_path)

    @property
    def sample_count(self) -> int:
        return int(self.time_s.size)

    @property
    def signal_names(self) -> tuple[str, ...]:
        return tuple(self.signals)

    @property
    def duration_s(self) -> float:
        if self.time_s.size < 2:
            return 0.0
        return float(self.time_s[-1] - self.time_s[0])


class ScanPattern(str, Enum):
    SAME_DIRECTION = "same_direction"
    SERPENTINE = "serpentine"


@dataclass(slots=True)
class DualOffsetParams:
    rows: int
    cols: int
    row_a_s: float
    row_b_s: float
    rows_apart: int
    row_offset: int
    point_a_s: float
    point_b_s: float
    points_apart: int
    point_offset: int
    scan_pattern: ScanPattern = ScanPattern.SAME_DIRECTION
    first_row_ltr: bool = True
    use_median: bool = True

    def __post_init__(self) -> None:
        if int(self.rows) != self.rows or self.rows < 1:
            raise ValueError("rows must be a positive integer.")
        if int(self.cols) != self.cols or self.cols < 1:
            raise ValueError("cols must be a positive integer.")
        self.rows = int(self.rows)
        self.cols = int(self.cols)
        if int(self.rows_apart) != self.rows_apart or self.rows_apart < 1:
            raise ValueError("rows_apart must be a positive integer.")
        if int(self.points_apart) != self.points_apart or self.points_apart < 1:
            raise ValueError("points_apart must be a positive integer.")
        self.rows_apart = int(self.rows_apart)
        self.points_apart = int(self.points_apart)
        if not 0 <= int(self.row_offset) < self.rows:
            raise ValueError("row_offset must be zero-based and within the map rows.")
        if not 0 <= int(self.point_offset) < self.cols:
            raise ValueError("point_offset must be zero-based and within the map columns.")
        self.row_offset = int(self.row_offset)
        self.point_offset = int(self.point_offset)
        anchors = (self.row_a_s, self.row_b_s, self.point_a_s, self.point_b_s)
        if not all(np.isfinite(float(value)) for value in anchors):
            raise ValueError("Timing anchors must be finite.")
        self.row_a_s = float(self.row_a_s)
        self.row_b_s = float(self.row_b_s)
        self.point_a_s = float(self.point_a_s)
        self.point_b_s = float(self.point_b_s)
        self.scan_pattern = ScanPattern(self.scan_pattern)
        self.first_row_ltr = bool(self.first_row_ltr)
        self.use_median = bool(self.use_median)


@dataclass(frozen=True, slots=True)
class TimingSolution:
    row_period_s: float
    row_ref0_s: float
    point_period_s: float
    pixel1_phase_s: float


@dataclass(slots=True)
class ReconstructionResult:
    values: np.ndarray
    sample_counts: np.ndarray
    timing: TimingSolution
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.values = np.asarray(self.values, dtype=float)
        self.sample_counts = np.asarray(self.sample_counts, dtype=int)
        if self.values.ndim != 2 or self.sample_counts.shape != self.values.shape:
            raise ValueError("values and sample_counts must be matching 2-D arrays.")
        self.warnings = list(self.warnings)
