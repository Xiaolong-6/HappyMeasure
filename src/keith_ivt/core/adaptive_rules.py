from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Iterable


class AdaptiveSpacing(str, Enum):
    LINEAR = "linear"
    LOG = "log"


@dataclass(frozen=True)
class AdaptiveSegment:
    start: float
    stop: float
    points: int
    spacing: AdaptiveSpacing | str = AdaptiveSpacing.LOG
    enabled: bool = True

    def normalized_spacing(self) -> AdaptiveSpacing:
        raw = self.spacing.value if isinstance(self.spacing, AdaptiveSpacing) else str(self.spacing).lower()
        return AdaptiveSpacing.LOG if raw.startswith("log") else AdaptiveSpacing.LINEAR


@dataclass(frozen=True)
class AdaptiveSweepRule:
    """Python-native adaptive sweep rule.

    This deliberately borrows the MATLAB app's measurement idea (sweep plans and
    debug-first validation) without copying MATLAB's class/package layout. The
    UI edits a list of enabled segments; the core returns source values and
    warnings that can be tested without Tk or hardware.
    """

    segments: tuple[AdaptiveSegment, ...] = field(default_factory=tuple)
    name: str = "Adaptive rule"

    def generate_values(self, *, deduplicate_boundaries: bool = True) -> list[float]:
        values: list[float] = []
        for segment in self.segments:
            if not segment.enabled:
                continue
            part = segment_values(segment)
            if deduplicate_boundaries and values and part and math.isclose(values[-1], part[0], rel_tol=1e-12, abs_tol=1e-15):
                part = part[1:]
            values.extend(part)
        if not values:
            raise ValueError("Adaptive rule produced no values.")
        return values

    def validate(self, max_points: int = 100_000) -> tuple[list[float], list[str]]:
        values = self.generate_values()
        warnings: list[str] = []
        if len(values) > max_points:
            raise ValueError(f"Adaptive rule produced {len(values)} points, above the {max_points} point limit.")
        if len(values) > 5000:
            warnings.append(f"Large adaptive plan: {len(values)} points.")
        if any(math.isnan(v) or math.isinf(v) for v in values):
            raise ValueError("Adaptive rule produced NaN or infinite source values.")
        return values, warnings


def _linspace(start: float, stop: float, count: int) -> list[float]:
    count = int(count)
    if count <= 0:
        raise ValueError("points must be positive")
    if count == 1:
        return [float(start)]
    return [float(start) + (float(stop) - float(start)) * i / (count - 1) for i in range(count)]


def _positive_logspace(start: float, stop: float, count: int) -> list[float]:
    if start <= 0 or stop <= 0:
        raise ValueError("log spacing needs non-zero endpoints with the same sign")
    if count == 1:
        return [float(start)]
    a = math.log10(start)
    b = math.log10(stop)
    return [10 ** (a + (b - a) * i / (count - 1)) for i in range(count)]


def _signed_logspace(start: float, stop: float, count: int) -> list[float]:
    start = float(start)
    stop = float(stop)
    if start == 0 or stop == 0 or (start > 0) != (stop > 0):
        raise ValueError("log segment cannot cross or include zero; split it into separate segments.")
    sign = 1.0 if start > 0 else -1.0
    mags = _positive_logspace(abs(start), abs(stop), count)
    return [sign * x for x in mags]


def segment_values(segment: AdaptiveSegment) -> list[float]:
    count = int(segment.points)
    if count <= 0:
        raise ValueError("Segment points must be positive.")
    spacing = segment.normalized_spacing()
    if spacing is AdaptiveSpacing.LINEAR:
        return _linspace(segment.start, segment.stop, count)
    return _signed_logspace(segment.start, segment.stop, count)


def default_log_rule() -> AdaptiveSweepRule:
    return AdaptiveSweepRule(
        name="Default log adaptive",
        segments=(AdaptiveSegment(1e-3, 1.0, 31, AdaptiveSpacing.LOG, True),),
    )


def rule_from_table(start: float, stop: float, points: int, spacing: str = "log") -> AdaptiveSweepRule:
    return AdaptiveSweepRule(segments=(AdaptiveSegment(start, stop, int(points), spacing, True),), name="Table adaptive rule")


def logic_from_rule(rule: AdaptiveSweepRule) -> str:
    values = rule.generate_values()
    return "values = [" + ", ".join(f"{v:.12g}" for v in values) + "]"


def values_from_segments(rows: Iterable[dict]) -> list[float]:
    segments = []
    for row in rows:
        if not row.get("enabled", True):
            continue
        segments.append(AdaptiveSegment(float(row["start"]), float(row["stop"]), int(row["points"]), str(row.get("spacing", "log")), True))
    return AdaptiveSweepRule(tuple(segments)).generate_values()
