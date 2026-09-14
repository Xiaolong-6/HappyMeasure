from __future__ import annotations

from tkinter import StringVar, ttk

from keith_ivt.ui.mixin_typing import UiMixinTyping
from keith_ivt.ui.plot_views import PlotView
from keith_ivt.ui.time_plot_settings import TIME_HISTORY_MODES, normalize_history_points
from keith_ivt.ui.widgets import add_tip


class TimePlotLiveControlsMixin(UiMixinTyping):
    """Keep Time-history display controls editable while a measurement is running."""

    def _build_plot_panel(self) -> None:
        super()._build_plot_panel()
        toolbar = self.views_frame.master
        self.time_history_live_frame = ttk.Frame(toolbar, style="ToolbarInner.TFrame")
        self.time_history_live_frame.grid(row=0, column=2, sticky="e", padx=(12, 0))

        ttk.Label(self.time_history_live_frame, text="History", style="Card.TLabel").grid(
            row=0, column=0, sticky="e", padx=(0, 5)
        )
        self.time_history_live_combo = ttk.Combobox(
            self.time_history_live_frame,
            textvariable=self.time_plot_history_mode,
            values=TIME_HISTORY_MODES,
            state="readonly",
            width=13,
        )
        self.time_history_live_combo.grid(row=0, column=1, sticky="e")

        self.time_history_live_points_text = StringVar(
            value=str(self.time_plot_history_points.get())
        )
        self.time_history_live_points = ttk.Spinbox(
            self.time_history_live_frame,
            from_=1,
            to=10_000_000,
            textvariable=self.time_history_live_points_text,
            width=7,
        )
        self.time_history_live_points.grid(row=0, column=2, sticky="e", padx=(5, 0))

        add_tip(
            self.time_history_live_combo,
            "Live display only: switch between the complete Time trace and a rolling Last N window. Acquired/exported data remain complete.",
        )
        add_tip(
            self.time_history_live_points,
            "Number of most-recent points shown when History is Last N points. This can be changed while measuring.",
        )

        self.time_history_live_combo.bind(
            "<<ComboboxSelected>>", self._on_live_time_history_mode_changed, add="+"
        )
        self.time_history_live_points.bind(
            "<Return>", self._on_live_time_history_points_changed, add="+"
        )
        self.time_history_live_points.bind(
            "<FocusOut>", self._on_live_time_history_points_changed, add="+"
        )
        self._refresh_time_history_live_controls()

    def _refresh_time_history_live_controls(self) -> None:
        frame = getattr(self, "time_history_live_frame", None)
        if frame is None:
            return
        try:
            time_visible = bool(self.plot_view_vars[PlotView.SIGNAL_TIME].get())
            if time_visible:
                frame.grid()
            else:
                frame.grid_remove()
            points = getattr(self, "time_history_live_points", None)
            if points is not None:
                points.configure(
                    state=(
                        "normal"
                        if self.time_plot_history_mode.get() == "Last N points"
                        else "disabled"
                    )
                )
            text_var = getattr(self, "time_history_live_points_text", None)
            if text_var is not None:
                text_var.set(str(normalize_history_points(self.time_plot_history_points.get())))
        except Exception:
            pass

    def _on_live_time_history_mode_changed(self, _event=None) -> None:
        self._refresh_time_history_live_controls()
        self._on_time_plot_settings_changed()

    def _on_live_time_history_points_changed(self, _event=None) -> None:
        text_var = getattr(self, "time_history_live_points_text", None)
        if text_var is None:
            return
        try:
            value = normalize_history_points(text_var.get())
            if str(value) != str(text_var.get()).strip():
                raise ValueError
        except Exception:
            value = normalize_history_points(self.time_plot_history_points.get())
            text_var.set(str(value))
            return
        self.time_plot_history_points.set(value)
        text_var.set(str(value))
        self._on_time_plot_settings_changed()

    def _on_plot_view_changed(self) -> None:
        super()._on_plot_view_changed()
        self._refresh_time_history_live_controls()

    def _apply_default_views_for_sweep_kind(self, kind: str | None = None) -> None:
        super()._apply_default_views_for_sweep_kind(kind)
        self._refresh_time_history_live_controls()


__all__ = ["TimePlotLiveControlsMixin"]
