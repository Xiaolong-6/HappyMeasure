"""Performance-optimized plot rendering with incremental updates.

This module provides optimized plotting strategies for real-time data visualization:
1. Incremental line updates (avoid full redraw)
2. Blitting for faster canvas updates
3. Downsampling for large datasets
4. Line object reuse to minimize matplotlib overhead
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.lines import Line2D
    from matplotlib.figure import Figure


class PlotOptimizer:
    """Optimize matplotlib plotting for real-time measurement data.

    This class maintains Line2D objects and updates their data instead of
    recreating them on every draw. This significantly improves performance
    for live sweeps with many data points.

    Usage:
        >>> optimizer = PlotOptimizer()
        >>> # First call creates lines
        >>> optimizer.update_lines(axes, new_data)
        >>> # Subsequent calls just update data (much faster)
        >>> optimizer.update_lines(axes, more_data)
    """

    def __init__(self, max_points_for_downsample: int = 1000):
        """Initialize plot optimizer.

        Args:
            max_points_for_downsample: Threshold for automatic downsampling
        """
        self._line_cache: dict[str, Line2D] = {}
        self._max_points = max_points_for_downsample
        self._last_draw_time = 0.0
        self._min_draw_interval = 0.05  # 50ms minimum between draws (20 FPS cap)

    def should_redraw(self) -> bool:
        """Check if enough time has passed for a redraw (frame rate limiting).

        Returns:
            True if redraw is allowed based on minimum interval
        """
        now = time.monotonic()
        if now - self._last_draw_time >= self._min_draw_interval:
            return True
        return False

    def downsample_if_needed(self, x: list[float], y: list[float]) -> tuple[list[float], list[float]]:
        """Downsample data if it exceeds the threshold.

        Uses LTTB (Largest-Triangle-Three-Buckets) inspired simple decimation
        for visual fidelity while reducing render load.

        Args:
            x: X coordinates
            y: Y coordinates

        Returns:
            Downsampled (x, y) tuples if needed, otherwise original data
        """
        if len(x) <= self._max_points:
            return x, y

        # Simple uniform decimation (fast and effective for most cases)
        step = len(x) // self._max_points
        x_ds = x[::step]
        y_ds = y[::step]

        # Always include last point
        if x_ds[-1] != x[-1]:
            x_ds.append(x[-1])
            y_ds.append(y[-1])

        return x_ds, y_ds

    def update_or_create_line(
        self,
        ax: Axes,
        key: str,
        x: list[float],
        y: list[float],
        **kwargs: Any,
    ) -> Line2D:
        """Update existing line or create new one.

        This is the core optimization: reuse Line2D objects instead of
        creating new ones on every draw.

        Args:
            ax: Matplotlib axes
            key: Unique identifier for this line (e.g., "trace_123_linear")
            x: X data
            y: Y data
            **kwargs: Line style arguments (color, linewidth, etc.)

        Returns:
            The Line2D object (new or updated)
        """
        # Apply downsampling if needed
        x_plot, y_plot = self.downsample_if_needed(x, y)

        # Check cache for existing line.  Matplotlib invalidates artists when
        # the figure or axes are cleared.  A cached Line2D can therefore point
        # to an old Axes after a full redraw, theme/layout change, or the
        # initial "Waiting for data..." live placeholder.  In that case,
        # updating the cached object succeeds but nothing appears on the
        # visible canvas.  Recreate the line whenever the cached artist is no
        # longer attached to this exact Axes.
        if key in self._line_cache:
            line = self._line_cache[key]
            line_axes = getattr(line, "axes", None)
            line_list = getattr(line_axes, "lines", []) if line_axes is not None else []
            if line_axes is ax and line in line_list:
                # Update data (much faster than recreating)
                line.set_xdata(x_plot)
                line.set_ydata(y_plot)

                # Update style if kwargs changed
                if kwargs:
                    line.set(**kwargs)

                return line

            # Stale artist: discard it and create a fresh line on the active Axes.
            self._line_cache.pop(key, None)

        # Create new line
        line = ax.plot(x_plot, y_plot, **kwargs)[0]
        self._line_cache[key] = line
        return line

    def clear_cache(self, prefix: str | None = None) -> None:
        """Clear cached lines.

        Args:
            prefix: If provided, only clear keys starting with this prefix
        """
        if prefix is None:
            self._line_cache.clear()
        else:
            self._line_cache = {
                k: v for k, v in self._line_cache.items()
                if not k.startswith(prefix)
            }

    def remove_stale_lines(self, active_keys: set[str]) -> None:
        """Remove lines that are no longer active.

        Args:
            active_keys: Set of keys that should remain
        """
        stale_keys = set(self._line_cache.keys()) - active_keys
        for key in stale_keys:
            line = self._line_cache.pop(key)
            # Remove from axes if the artist is still attached.  Prefer
            # Line2D.remove() for current Matplotlib, but keep a list-removal
            # fallback for simple test doubles.
            axes = getattr(line, "axes", None)
            lines = getattr(axes, "lines", []) if axes is not None else []
            try:
                line.remove()
            except Exception:
                pass
            # Some tests use simple mocks where remove() is a no-op.  Keep the
            # fallback deterministic without depending on Matplotlib internals.
            if line in lines:
                lines.remove(line)

    def mark_draw_complete(self) -> None:
        """Record that a draw operation completed."""
        self._last_draw_time = time.monotonic()


class FastPlotRenderer:
    """High-level renderer using PlotOptimizer for efficient drawing.

    This wraps the optimizer with a convenient interface for the HappyMeasure
    plot panel workflow.
    """

    def __init__(self, figure: Figure, max_points: int = 1000):
        """Initialize fast renderer.

        Args:
            figure: Matplotlib figure to render on
            max_points: Maximum points before downsampling
        """
        self.figure = figure
        self.optimizer = PlotOptimizer(max_points_for_downsample=max_points)
        self._axes_cache: dict[int, Axes] = {}

    def prepare_axes(self, num_subplots: int, rows: int, cols: int) -> list[Axes]:
        """Create or reuse subplot axes.

        Args:
            num_subplots: Number of subplots needed
            rows: Grid rows
            cols: Grid columns

        Returns:
            List of axes objects
        """
        # Clear existing axes if count changed
        if len(self.figure.axes) != num_subplots:
            self.figure.clear()
            self.optimizer.clear_cache()

        axes = []
        for idx in range(num_subplots):
            if idx < len(self.figure.axes):
                ax = self.figure.axes[idx]
            else:
                ax = self.figure.add_subplot(rows, cols, idx + 1)
            axes.append(ax)

        return axes

    def draw_incremental(
        self,
        axes: list[Axes],
        data_series: list[dict[str, Any]],
    ) -> None:
        """Draw multiple data series incrementally.

        Args:
            axes: List of axes to draw on
            data_series: List of dicts with keys:
                - ax_index: Which axis to draw on
                - key: Unique identifier for the line
                - x: X data
                - y: Y data
                - style: Dict of line style kwargs
        """
        active_keys: set[str] = set()

        touched_axes: set[Axes] = set()

        for series in data_series:
            ax_idx = series["ax_index"]
            key = series["key"]
            x = series["x"]
            y = series["y"]
            style = series.get("style", {})

            if ax_idx < len(axes):
                ax = axes[ax_idx]
                # Remove transient placeholder text from the empty-live-plot state.
                texts = getattr(ax, "texts", [])
                try:
                    iterable_texts = list(texts)
                except TypeError:
                    iterable_texts = []
                for text in iterable_texts:
                    if text.get_text() == "Waiting for data...":
                        text.remove()
                self.optimizer.update_or_create_line(ax, key, x, y, **style)
                active_keys.add(key)
                touched_axes.add(ax)

        # Remove stale lines
        self.optimizer.remove_stale_lines(active_keys)

        # Incremental Line2D updates do not update Matplotlib data limits by
        # themselves.  Recompute limits after every live update; otherwise a
        # sweep such as -5 V -> +5 V can remain outside the default 0..1 view
        # and appear as if real-time plotting is blank.
        for ax in touched_axes:
            ax.relim()
            ax.autoscale_view(scalex=True, scaley=True)

        # Trigger draw if rate limit allows
        if self.optimizer.should_redraw():
            self.figure.canvas.draw_idle()
            self.optimizer.mark_draw_complete()

    def reset(self) -> None:
        """Reset renderer state (clear all caches)."""
        self.figure.clear()
        self.optimizer.clear_cache()
