from __future__ import annotations

from dataclasses import dataclass

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
