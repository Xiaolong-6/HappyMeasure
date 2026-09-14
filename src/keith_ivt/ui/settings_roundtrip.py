"""Close the persistence gap between live Tk settings and ``AppSettings``.

``SettingsPresetMixin`` predates several application-level settings and builds
an ``AppSettings`` snapshot explicitly. Keep the compatibility overlay small
and test its field parity so a newly persisted setting cannot silently fall
back to a dataclass default when the Review Default Settings dialog is used.
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from keith_ivt.data.settings import AppSettings, load_settings, save_settings
from keith_ivt.instrument.simulator import debug_model_names
from keith_ivt.ui.mixin_typing import UiMixinTyping

CURRENT_SETTINGS_OVERLAY_FIELDS = frozenset(
    {"check_updates_on_startup", "auto_save_backup", "record_log"}
)


class SettingsRoundTripMixin(UiMixinTyping):
    """Overlay settings that are owned outside the legacy snapshot builder."""

    def _current_settings(self) -> AppSettings:
        base = cast(AppSettings, getattr(super(), "_current_settings")())
        current_settings = getattr(self, "settings", None)

        # ``check_updates_on_startup`` used to be assumed to have a dedicated
        # Tk variable. Keep supporting such a variable if one exists, while all
        # application-only preferences safely fall back to AppSettings.
        live_var = getattr(self, "check_updates_on_startup", None)
        if live_var is not None and hasattr(live_var, "get"):
            check_updates = bool(live_var.get())
        else:
            check_updates = bool(
                getattr(current_settings, "check_updates_on_startup", base.check_updates_on_startup)
            )

        return replace(
            base,
            check_updates_on_startup=check_updates,
            auto_save_backup=bool(
                getattr(current_settings, "auto_save_backup", base.auto_save_backup)
            ),
            record_log=bool(getattr(current_settings, "record_log", base.record_log)),
        )

    def review_and_save_settings(self):
        """Review persistent app defaults, including data-safety preferences."""
        settings = self._current_settings()
        fields = {
            # Logging, cache, and automatic data protection
            "record_log": settings.record_log,
            "auto_save_backup": settings.auto_save_backup,
            "log_max_kb": max(10, int((settings.log_max_bytes + 1023) // 1024)),
            "cache_enabled": settings.cache_enabled,
            "cache_interval_points": settings.cache_interval_points,
            # Hardware connection defaults
            "default_port": settings.default_port,
            "default_baud_rate": settings.default_baud_rate,
            "default_terminal": settings.default_terminal,
            "default_sense_mode": settings.default_sense_mode,
            # Plot and display
            "default_plot_layout": settings.default_plot_layout,
            "time_plot_marker_mode": settings.time_plot_marker_mode,
            "time_plot_history_mode": settings.time_plot_history_mode,
            "time_plot_history_points": settings.time_plot_history_points,
            "time_plot_refresh_ms": settings.time_plot_refresh_ms,
            # UI appearance / application behavior
            "ui_font_family": settings.ui_font_family,
            "ui_font_size": settings.ui_font_size,
            "ui_theme": settings.ui_theme,
            "show_front_panel_on_start": settings.show_front_panel_on_start,
            "check_updates_on_startup": settings.check_updates_on_startup,
            # Debug settings
            "default_debug": settings.default_debug,
            "default_debug_model": settings.default_debug_model,
        }

        chosen = self._review_dict_dialog(
            "Default Settings",
            fields,
            choices={
                "default_terminal": ["FRON", "REAR"],
                "default_sense_mode": ["2W", "4W"],
                "default_plot_layout": ["Auto", "Horizontal", "Vertical"],
                "time_plot_marker_mode": ["Auto", "On", "Off"],
                "time_plot_history_mode": ["All data", "Last N points"],
                "time_plot_refresh_ms": [100, 250, 500, 1000],
                "ui_font_family": (
                    self._available_ui_fonts()
                    if hasattr(self, "_available_ui_fonts")
                    else ["Verdana"]
                ),
                "ui_theme": ["Light", "Dark", "Debug"],
                "default_debug_model": debug_model_names(),
            },
        )
        if chosen is None:
            return

        current = load_settings()
        data = current.__dict__.copy()
        chosen = dict(chosen)
        if "log_max_kb" in chosen:
            try:
                chosen["log_max_bytes"] = int(float(chosen.pop("log_max_kb"))) * 1024
            except Exception:
                chosen.pop("log_max_kb", None)
        data.update(chosen)
        path = save_settings(AppSettings(**data))
        self._apply_saved_settings_feedback(data, chosen, path)


__all__ = ["CURRENT_SETTINGS_OVERLAY_FIELDS", "SettingsRoundTripMixin"]
