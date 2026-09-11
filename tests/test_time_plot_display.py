"""Focused tests for display-only Time plot policies."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from keith_ivt.ui.time_plot_settings import (
    normalize_history_points,
    normalize_refresh_interval_ms,
    time_display_window,
    time_marker_for,
)
from keith_ivt.data.settings import AppSettings, sanitize_settings_dict


def test_last_n_window_is_display_only_and_keeps_the_newest_points() -> None:
    x = list(range(10_000))
    y = [value * 2 for value in x]

    shown_x, shown_y = time_display_window(x, y, "Last N points", 5_000)

    assert len(shown_x) == len(shown_y) == 5_000
    assert shown_x[0] == 5_000
    assert shown_x[-1] == 9_999
    assert len(x) == len(y) == 10_000


def test_history_window_handles_multiple_lengths_and_invalid_counts() -> None:
    first_x, first_y = time_display_window([1, 2, 3], [4, 5, 6], "Last N points", 99)
    second_x, second_y = time_display_window(list(range(7)), list(range(7, 14)), "Last N points", 2)

    assert (first_x, first_y) == ([1, 2, 3], [4, 5, 6])
    assert (second_x, second_y) == ([5, 6], [12, 13])
    assert normalize_history_points(0) == 1
    assert normalize_history_points(-20) == 1
    assert normalize_history_points("not-a-number") == 5_000


def test_all_data_and_mismatched_source_lengths_are_safe() -> None:
    shown_x, shown_y = time_display_window([1, 2, 3], [10, 20], "All data", 1)

    assert (shown_x, shown_y) == ([1, 2], [10, 20])


def test_time_marker_policy_has_auto_threshold_and_explicit_overrides() -> None:
    assert time_marker_for("Auto", 1_500) == "."
    assert time_marker_for("Auto", 1_501) is None
    assert time_marker_for("On", 100_000) == "."
    assert time_marker_for("Off", 1) is None


def test_refresh_interval_accepts_supported_choices_only() -> None:
    assert normalize_refresh_interval_ms(100) == 100
    assert normalize_refresh_interval_ms("500") == 500
    assert normalize_refresh_interval_ms(333) == 250
    assert normalize_refresh_interval_ms("invalid") == 250


def test_time_plot_settings_have_safe_defaults_and_sanitize_legacy_values() -> None:
    defaults = AppSettings()
    sanitized = sanitize_settings_dict(
        {
            "time_plot_marker_mode": "not-a-mode",
            "time_plot_history_mode": "all",
            "time_plot_history_points": 0,
            "time_plot_refresh_ms": 333,
        }
    )

    assert defaults.time_plot_marker_mode == "Auto"
    assert defaults.time_plot_history_mode == "Last N points"
    assert defaults.time_plot_history_points == 5_000
    assert defaults.time_plot_refresh_ms == 250
    assert sanitized["time_plot_marker_mode"] == "Auto"
    assert sanitized["time_plot_history_mode"] == "Last N points"
    assert sanitized["time_plot_history_points"] == 1
    assert sanitized["time_plot_refresh_ms"] == 250


def test_live_queue_throttle_and_completion_refresh_contracts() -> None:
    root = Path(__file__).resolve().parents[1]
    controller = (root / "src/keith_ivt/ui/sweep_controller.py").read_text(encoding="utf-8")
    panel = (root / "src/keith_ivt/ui/plot_panel.py").read_text(encoding="utf-8")

    assert "self._live_plot_refresh_due()" in controller
    assert "self._redraw_all_plots(live_only=True, force=True)" in controller
    assert "self._redraw_all_plots()" in controller
    assert "draw_incremental(axes, data_series, force=force)" in panel
