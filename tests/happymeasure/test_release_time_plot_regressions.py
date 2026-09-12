from __future__ import annotations

from unittest.mock import Mock

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure

from keith_ivt.models import SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui.plot_optimizer import FastPlotRenderer, extrema_envelope
from keith_ivt.ui.plot_panel import PlotPanelMixin
from keith_ivt.ui.plot_views import PlotView


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


def _panel() -> PlotPanelMixin:
    panel = object.__new__(PlotPanelMixin)
    panel.time_plot_history_mode = _Value("Last N points")
    panel.time_plot_history_points = _Value(5_000)
    panel.plot_x_unit = _Value("Auto")
    panel.plot_y_unit = _Value("Auto")
    panel._swapped_views = set()
    return panel


def test_live_last_n_limits_before_coordinate_preparation(monkeypatch) -> None:
    result = _large_time_result()
    panel = _panel()
    prepared_lengths: list[tuple[PlotView, int]] = []

    def record_xy(view_result, view):
        prepared_lengths.append((view, len(view_result.points)))
        count = len(view_result.points)
        return [0.0] * count, [0.0] * count, "X", "Y", "Time", False

    monkeypatch.setattr("keith_ivt.ui.plot_panel.xy_for_view", record_xy)
    panel._prepare_view_data(result, PlotView.SIGNAL_TIME, live=True)
    panel._prepare_view_data(result, PlotView.SIGNAL_TIME, live=False)

    assert prepared_lengths == [
        (PlotView.SIGNAL_TIME, 5_000),
        (PlotView.SIGNAL_TIME, 76_677),
    ]
    assert len(result.points) == 76_677


def test_live_result_does_not_copy_full_history_when_only_last_n_is_needed() -> None:
    result = _large_time_result()

    class NoFullIterationList(list):
        def __iter__(self):
            raise AssertionError("live Time path copied the complete point history")

    panel = _panel()
    panel._live_config = result.config
    panel._live_points = NoFullIterationList(result.points)
    live_time = panel._live_result_for_view(PlotView.SIGNAL_TIME)

    assert live_time is not None
    assert len(live_time.points) == 5_000
    assert len(panel._live_points) == 76_677


def test_completed_time_trace_ignores_live_last_n_setting() -> None:
    result = _large_time_result(70_000)
    completed = _panel()._prepare_view_data(result, PlotView.SIGNAL_TIME, live=False)
    assert len(completed[0]) == 70_000
    assert completed[0][0] < completed[0][-1]


def test_static_envelope_spans_full_range_and_preserves_narrow_extrema() -> None:
    x = list(range(70_000))
    y = [0.0] * len(x)
    y[12_345] = 10.0
    y[54_321] = -8.0
    shown_x, shown_y = extrema_envelope(x, y)
    assert shown_x[0] == 0
    assert shown_x[-1] == 69_999
    assert max(shown_y) == 10.0
    assert min(shown_y) == -8.0


def test_live_time_axes_remain_stable_until_expansion_is_needed() -> None:
    fig = Figure(figsize=(4, 3), dpi=100)
    renderer = FastPlotRenderer(fig)
    axes = renderer.prepare_axes(num_subplots=1, rows=1, cols=1)
    series = {
        "ax_index": 0,
        "key": "live_Time",
        "x": [0.0, 1.0],
        "y": [0.0, 1.0],
        "time_view": True,
        "style": {"linestyle": "-"},
    }
    renderer.draw_incremental(axes, [series], force=True)
    initial_xlim = axes[0].get_xlim()
    initial_ylim = axes[0].get_ylim()

    series["x"] = [0.0, 1.01]
    series["y"] = [0.0, 1.01]
    renderer.draw_incremental(axes, [series], force=True)
    assert axes[0].get_xlim() == initial_xlim
    assert axes[0].get_ylim() == initial_ylim

    series["x"] = [0.0, 3.0]
    series["y"] = [0.0, 3.0]
    renderer.draw_incremental(axes, [series], force=True)
    assert axes[0].get_xlim()[1] > 3.0
    assert axes[0].get_ylim()[1] > 3.0


def test_force_refresh_bypasses_renderer_rate_limit() -> None:
    fig = Figure(figsize=(4, 3), dpi=100)
    renderer = FastPlotRenderer(fig)
    axes = renderer.prepare_axes(num_subplots=1, rows=1, cols=1)
    series = [
        {
            "ax_index": 0,
            "key": "live_Linear",
            "x": [0.0, 1.0],
            "y": [0.0, 1.0],
            "style": {"linestyle": "-"},
        }
    ]
    renderer.draw_incremental(axes, series)
    fig.canvas.draw_idle = Mock()
    renderer.draw_incremental(axes, series, force=True)
    assert fig.canvas.draw_idle.called
