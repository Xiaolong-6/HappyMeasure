from __future__ import annotations

from dataclasses import dataclass
import math

from keith_ivt.core.adaptive_logic import MAX_ADAPTIVE_POINTS
from keith_ivt.models import make_source_values


@dataclass(frozen=True)
class SegmentRow:
    start: float
    stop: float
    step: float
    enabled: bool = True


def values_from_segment_rows(rows: list[SegmentRow]) -> list[float]:
    """Generate source values from simple Start/Stop/Step rows.

    Duplicate boundary points are removed only at adjacent row boundaries, so a
    user can intentionally revisit earlier values by placing them in later rows.
    """
    values: list[float] = []
    for row in rows:
        if not row.enabled:
            continue
        segment = make_source_values(row.start, row.stop, row.step)
        if values and segment and abs(values[-1] - segment[0]) <= max(abs(row.step), 1.0) * 1e-12:
            segment = segment[1:]
        values.extend(segment)
    if not values:
        raise ValueError("At least one enabled adaptive/table row is required.")
    return values


def rows_from_tuples(rows: list[tuple[float, float, float]]) -> list[SegmentRow]:
    return [SegmentRow(float(a), float(b), float(c)) for a, b, c in rows]


def _display_number(value: float) -> str:
    return format(float(value), ".12g")


def _segment_point_count(start: float, stop: float, step: float) -> int:
    if step == 0:
        raise ValueError("step cannot be 0")
    if start < stop and step < 0:
        raise ValueError("ascending ranges require a positive step")
    if start > stop and step > 0:
        raise ValueError("descending ranges require a negative step")
    if start == stop:
        return 1
    span = (stop - start) / step
    if not math.isfinite(span):
        raise ValueError("range creates too many points")
    return int(math.floor(span + 1e-9)) + 1


def remove_duplicate_values(values: list[float]) -> list[float]:
    """Remove repeated values globally while preserving their first occurrence."""
    unique: list[float] = []
    seen: set[str] = set()
    for value in values:
        key = _display_number(value)
        if key in seen:
            continue
        seen.add(key)
        unique.append(float(value))
    return unique


def parse_segment_text(
    text: str,
    *,
    remove_duplicates: bool = True,
    max_points: int = MAX_ADAPTIVE_POINTS,
) -> list[float]:
    """Parse one ``start, stop, step`` segment per line in execution order."""
    values: list[float] = []
    found_segment = False
    for line_number, raw_line in enumerate((text or "").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        found_segment = True
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 3 or any(not field for field in fields):
            raise ValueError(
                f"Line {line_number}: expected exactly start, stop, step separated by commas."
            )
        try:
            start, stop, step = (float(field) for field in fields)
        except ValueError as exc:
            raise ValueError(f"Line {line_number}: all three values must be numbers.") from exc
        if not all(math.isfinite(value) for value in (start, stop, step)):
            raise ValueError(f"Line {line_number}: NaN and infinite values are not allowed.")
        try:
            point_count = _segment_point_count(start, stop, step)
        except ValueError as exc:
            raise ValueError(f"Line {line_number}: {exc}.") from exc
        if point_count > max_points or len(values) + point_count > max_points:
            raise ValueError(
                f"Line {line_number}: the complete Adaptive sweep exceeds {max_points} points."
            )
        values.extend(make_source_values(start, stop, step))
        if len(values) > max_points:
            raise ValueError(
                f"Line {line_number}: the complete Adaptive sweep exceeds {max_points} points."
            )
    if not found_segment:
        raise ValueError("Enter at least one Adaptive segment.")
    if remove_duplicates:
        values = remove_duplicate_values(values)
    if not values:
        raise ValueError("Adaptive segments produced no source values.")
    return values
