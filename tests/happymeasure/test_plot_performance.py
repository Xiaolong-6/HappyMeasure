"""Behavioral tests for plot performance primitives."""

from __future__ import annotations

import time
from unittest.mock import Mock

from keith_ivt.ui.plot_optimizer import FastPlotRenderer, PlotOptimizer


class TestPlotOptimizer:
    def test_downsample_small_dataset(self) -> None:
        optimizer = PlotOptimizer(max_points_for_downsample=1000)
        x = list(range(100))
        y = list(range(100))

        x_ds, y_ds = optimizer.downsample_if_needed(x, y)

        assert x_ds == x
        assert y_ds == y

    def test_downsample_large_dataset_preserves_endpoints(self) -> None:
        optimizer = PlotOptimizer(max_points_for_downsample=100)
        x = list(range(1000))
        y = list(range(1000))

        x_ds, y_ds = optimizer.downsample_if_needed(x, y)

        assert len(x_ds) <= 101
        assert len(x_ds) == len(y_ds)
        assert x_ds[0] == 0
        assert x_ds[-1] == 999

    def test_frame_rate_limiting(self) -> None:
        optimizer = PlotOptimizer()

        assert optimizer.should_redraw() is True
        optimizer.mark_draw_complete()
        assert optimizer.should_redraw() is False
        time.sleep(0.06)
        assert optimizer.should_redraw() is True

    def test_line_cache_reuses_existing_artist(self) -> None:
        optimizer = PlotOptimizer()
        ax = Mock()
        line = Mock()
        ax.lines = [line]
        line.axes = ax
        ax.plot.return_value = [line]

        first = optimizer.update_or_create_line(ax, "trace", [1, 2], [3, 4])
        ax.plot.reset_mock()
        second = optimizer.update_or_create_line(ax, "trace", [1, 2, 3], [4, 5, 6])

        assert first is second
        assert not ax.plot.called
        assert line.set_xdata.called
        assert line.set_ydata.called

    def test_clear_cache_with_prefix(self) -> None:
        optimizer = PlotOptimizer()
        optimizer._line_cache["trace_1"] = Mock()
        optimizer._line_cache["trace_2"] = Mock()
        optimizer._line_cache["live_1"] = Mock()

        optimizer.clear_cache(prefix="trace_")

        assert set(optimizer._line_cache) == {"live_1"}

    def test_remove_stale_lines(self) -> None:
        optimizer = PlotOptimizer()
        active = Mock()
        active.axes.lines = [active]
        stale = Mock()
        stale.axes.lines = [stale]
        optimizer._line_cache["active"] = active
        optimizer._line_cache["stale"] = stale

        optimizer.remove_stale_lines(active_keys={"active"})

        assert "active" in optimizer._line_cache
        assert "stale" not in optimizer._line_cache
        assert stale.axes.lines == []


class TestFastPlotRenderer:
    @staticmethod
    def _series(x=None, y=None):
        return [
            {
                "ax_index": 0,
                "key": "live_Linear",
                "x": [0.0, 1.0] if x is None else x,
                "y": [0.0, 1.0] if y is None else y,
                "style": {"label": "live", "linestyle": "-"},
            }
        ]

    def test_prepare_axes_creates_requested_subplots(self) -> None:
        figure = Mock()
        figure.axes = []
        figure.add_subplot = Mock(return_value=Mock())
        renderer = FastPlotRenderer(figure)

        axes = renderer.prepare_axes(num_subplots=3, rows=1, cols=3)

        assert len(axes) == 3
        assert figure.add_subplot.call_count == 3

    def test_prepare_axes_reuses_matching_axes(self) -> None:
        figure = Mock()
        existing = [Mock(), Mock()]
        figure.axes = existing
        renderer = FastPlotRenderer(figure)

        assert renderer.prepare_axes(num_subplots=2, rows=1, cols=2) == existing

    def test_draw_incremental_populates_line_cache(self) -> None:
        figure = Mock()
        figure.axes = []
        ax = Mock()
        figure.add_subplot.return_value = ax
        ax.plot.return_value = [Mock()]
        renderer = FastPlotRenderer(figure)
        axes = renderer.prepare_axes(1, 1, 1)

        renderer.draw_incremental(axes, self._series())

        assert "live_Linear" in renderer.optimizer._line_cache

    def test_reset_clears_renderer_state(self) -> None:
        figure = Mock()
        figure.axes = []
        figure.add_subplot.return_value = Mock()
        renderer = FastPlotRenderer(figure)
        renderer.optimizer._line_cache["trace"] = Mock()

        renderer.reset()

        assert renderer.optimizer._line_cache == {}
        assert figure.clear.called

    def test_incremental_draw_autoscales_live_data(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib.figure import Figure

        figure = Figure(figsize=(4, 3), dpi=100)
        renderer = FastPlotRenderer(figure)
        axes = renderer.prepare_axes(1, 1, 1)

        renderer.draw_incremental(
            axes,
            self._series(x=[-5.0, 0.0, 5.0], y=[-2e-6, 0.0, 2e-6]),
        )

        xlim = axes[0].get_xlim()
        ylim = axes[0].get_ylim()
        assert xlim[0] < -5.0 and xlim[1] > 5.0
        assert ylim[0] < -2e-6 and ylim[1] > 2e-6

    def test_force_draw_bypasses_rate_limit(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib.figure import Figure

        figure = Figure(figsize=(4, 3), dpi=100)
        renderer = FastPlotRenderer(figure)
        axes = renderer.prepare_axes(1, 1, 1)
        renderer.draw_incremental(axes, self._series())
        figure.canvas.draw_idle = Mock()

        renderer.draw_incremental(axes, self._series(), force=True)

        assert figure.canvas.draw_idle.called

    def test_cached_line_is_recreated_after_figure_clear(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib.figure import Figure

        figure = Figure(figsize=(4, 3), dpi=100)
        renderer = FastPlotRenderer(figure)
        first_axes = renderer.prepare_axes(1, 1, 1)
        renderer.draw_incremental(first_axes, self._series())
        old_line = renderer.optimizer._line_cache["live_Linear"]

        figure.clear()
        second_axes = renderer.prepare_axes(1, 1, 1)
        renderer.draw_incremental(
            second_axes,
            self._series(x=[-5.0, 0.0, 5.0], y=[-2e-6, 0.0, 2e-6]),
        )

        new_line = renderer.optimizer._line_cache["live_Linear"]
        assert new_line is not old_line
        assert new_line.axes is second_axes[0]
        assert new_line in second_axes[0].lines
        assert len(second_axes[0].lines) == 1
