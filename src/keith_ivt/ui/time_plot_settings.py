"""Headless policies for the Time plot's display-only settings."""

from __future__ import annotations

from collections.abc import Sequence

TIME_MARKER_MODES = ("Auto", "On", "Off")
TIME_HISTORY_MODES = ("All data", "Last N points")
TIME_REFRESH_INTERVALS_MS = (100, 250, 500, 1000)
TIME_MARKER_AUTO_THRESHOLD = 1500
DEFAULT_TIME_HISTORY_POINTS = 5000
DEFAULT_TIME_REFRESH_MS = 250
MIN_TIME_HISTORY_POINTS = 1
MAX_TIME_HISTORY_POINTS = 10_000_000


def normalize_marker_mode(value: object, default: str = "Auto") -> str:
    text = str(value).strip().title()
    return text if text in TIME_MARKER_MODES else default


def normalize_history_mode(value: object, default: str = "Last N points") -> str:
    text = str(value).strip().lower()
    aliases = {
        "all": "All data",
        "all data": "All data",
        "last n": "Last N points",
        "last n points": "Last N points",
    }
    return aliases.get(text, default)


def normalize_history_points(
    value: object,
    default: int = DEFAULT_TIME_HISTORY_POINTS,
    *,
    minimum: int = MIN_TIME_HISTORY_POINTS,
    maximum: int = MAX_TIME_HISTORY_POINTS,
) -> int:
    try:
        points = int(str(value).strip())
    except (TypeError, ValueError, OverflowError):
        points = int(default)
    return max(minimum, min(maximum, points))


def normalize_refresh_interval_ms(value: object, default: int = DEFAULT_TIME_REFRESH_MS) -> int:
    try:
        interval = int(str(value).strip())
    except (TypeError, ValueError, OverflowError):
        interval = int(default)
    return interval if interval in TIME_REFRESH_INTERVALS_MS else int(default)


def time_display_window(
    x: Sequence[float],
    y: Sequence[float],
    history_mode: object,
    history_points: object,
) -> tuple[list[float], list[float]]:
    """Return display-only X/Y data without mutating the source sequences."""
    pair_count = min(len(x), len(y))
    if pair_count <= 0:
        return [], []
    if normalize_history_mode(history_mode) == "All data":
        start = 0
    else:
        count = normalize_history_points(history_points)
        start = max(0, pair_count - count)
    return list(x[start:pair_count]), list(y[start:pair_count])


def time_marker_for(mode: object, displayed_points: int) -> str | None:
    """Return the Matplotlib marker for a Time trace, or ``None``."""
    normalized = normalize_marker_mode(mode)
    if normalized == "On":
        return "."
    if normalized == "Off":
        return None
    return "." if int(displayed_points) <= TIME_MARKER_AUTO_THRESHOLD else None
