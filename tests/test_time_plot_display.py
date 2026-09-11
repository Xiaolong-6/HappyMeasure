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
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui.plot_panel import PlotPanelMixin
from keith_ivt.ui.plot_optimizer import extrema_envelope
from keith_ivt.ui.plot_views import PlotView


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


class _Value:
    def __init__(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value


def _large_time_result(point_count: int = 76_677) -> SweepResult:
    config = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=1.0,
        step=0.1,
        compliance=0.01,
        sweep_kind=SweepKind.CONSTANT_TIME,
    )
    points = [
        SweepPoint(float(index), float(index) * 2.0, elapsed_s=float(index))
        for index in range(point_count)
    ]
    return SweepResult(config, points)


def test_time_last_n_limits_points_before_expensive_coordinate_preparation(monkeypatch) -> None:
    result = _large_time_result()
    panel = object.__new__(PlotPanelMixin)
    panel.time_plot_history_mode = _Value("Last N points")
    panel.time_plot_history_points = _Value(5_000)
    panel.plot_x_unit = _Value("Auto")
    panel.plot_y_unit = _Value("Auto")
    panel._swapped_views = set()
    prepared_lengths: list[tuple[PlotView, int]] = []

    def record_xy(view_result, view):
        prepared_lengths.append((view, len(view_result.points)))
        return (
            [0.0] * len(view_result.points),
            [0.0] * len(view_result.points),
            "X",
            "Y",
            "Time",
            False,
        )

    monkeypatch.setattr("keith_ivt.ui.plot_panel.xy_for_view", record_xy)

    panel._prepare_view_data(result, PlotView.LINEAR)
    time_data = panel._prepare_view_data(result, PlotView.SIGNAL_TIME, live=True)
    static_time_data = panel._prepare_view_data(result, PlotView.SIGNAL_TIME)

    assert prepared_lengths == [
        (PlotView.LINEAR, 76_677),
        (PlotView.SIGNAL_TIME, 5_000),
        (PlotView.SIGNAL_TIME, 76_677),
    ]
    assert len(time_data[0]) == 5_000
    assert len(static_time_data[0]) == 76_677
    assert len(result.points) == 76_677
    assert result.points[0].source_value == 0.0
    assert result.points[-1].source_value == 76_676.0
    assert panel._time_history_count() == 5_000


def test_completed_and_imported_time_traces_ignore_live_last_n_window() -> None:
    result = _large_time_result(70_000)
    panel = object.__new__(PlotPanelMixin)
    panel.time_plot_history_mode = _Value("Last N points")
    panel.time_plot_history_points = _Value(5_000)
    panel.plot_x_unit = _Value("Auto")
    panel.plot_y_unit = _Value("Auto")
    panel._swapped_views = set()

    completed = panel._prepare_view_data(result, PlotView.SIGNAL_TIME)
    imported = panel._prepare_view_data(result, PlotView.SIGNAL_TIME, live=False)

    assert len(completed[0]) == 70_000
    assert completed[0][0] == imported[0][0]
    assert completed[0][-1] == imported[0][-1]
    assert completed[0][-1] > completed[0][4_999]
    assert panel.time_plot_history_mode.get() == "Last N points"
    assert len(result.points) == 70_000


def test_live_time_view_builds_only_the_last_n_point_input() -> None:
    result = _large_time_result()

    class NoFullIterationList(list):
        def __iter__(self):
            raise AssertionError("the live Time path copied the full point list")

    panel = object.__new__(PlotPanelMixin)
    panel._live_config = result.config
    panel._live_points = NoFullIterationList(result.points)
    panel.time_plot_history_mode = _Value("Last N points")
    panel.time_plot_history_points = _Value(5_000)

    live_time = panel._live_result_for_view(PlotView.SIGNAL_TIME)

    assert live_time is not None
    assert len(live_time.points) == 5_000
    assert len(panel._live_points) == 76_677
    assert panel._live_points[0].source_value == 0.0
    assert live_time.points[0].source_value == 71_677.0


def test_static_time_envelope_spans_full_range_and_preserves_extrema() -> None:
    x = list(range(70_000))
    y = [0.0] * 70_000
    y[12_345] = 10.0
    y[54_321] = -8.0

    shown_x, shown_y = extrema_envelope(x, y)

    assert len(shown_x) <= 4_000
    assert shown_x[0] == 0
    assert shown_x[-1] == 69_999
    assert max(shown_y) == 10.0
    assert min(shown_y) == -8.0


def test_live_queue_throttle_and_completion_refresh_contracts() -> None:
    root = Path(__file__).resolve().parents[1]
    controller = (root / "src/keith_ivt/ui/sweep_controller.py").read_text(encoding="utf-8")
    panel = (root / "src/keith_ivt/ui/plot_panel.py").read_text(encoding="utf-8")
    controls = (root / "src/keith_ivt/ui/plot_controls.py").read_text(encoding="utf-8")
    traces = (root / "src/keith_ivt/ui/trace_panel.py").read_text(encoding="utf-8")

    assert "self._live_plot_refresh_due()" in controller
    assert "self._redraw_all_plots(live_only=True, force=True)" in controller
    assert "self._redraw_all_plots()" in controller
    assert "draw_incremental(axes, data_series, force=force)" in panel
    assert 'label="Time plot settings..."' in controls
    assert 'label="Time plot settings..."' not in traces
