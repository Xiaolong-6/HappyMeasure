"""Close the persistence gap between live Tk settings and ``AppSettings``.

``SettingsPresetMixin`` predates several application-level settings and builds
an ``AppSettings`` snapshot explicitly. Keep the compatibility overlay small
and test its field parity so a newly persisted setting cannot silently fall
back to a dataclass default when the Review Default Settings dialog is used.
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from keith_ivt.data.settings import AppSettings
from keith_ivt.ui.mixin_typing import UiMixinTyping

CURRENT_SETTINGS_OVERLAY_FIELDS = frozenset({"check_updates_on_startup"})


class SettingsRoundTripMixin(UiMixinTyping):
    """Overlay settings that are owned outside the legacy snapshot builder."""

    def _current_settings(self) -> AppSettings:
        base = cast(AppSettings, getattr(super(), "_current_settings")())

        # ``check_updates_on_startup`` is persisted application state, but it is
        # not required to have a dedicated live Tk variable. Older code assumed
        # ``self.check_updates_on_startup`` always existed, which made
        # Review Default Settings crash during normal app startup. Prefer a live
        # variable when one exists, otherwise use the current AppSettings value.
        live_var = getattr(self, "check_updates_on_startup", None)
        if live_var is not None and hasattr(live_var, "get"):
            check_updates = bool(live_var.get())
        else:
            current_settings = getattr(self, "settings", None)
            check_updates = bool(
                getattr(current_settings, "check_updates_on_startup", base.check_updates_on_startup)
            )

        return replace(
            base,
            check_updates_on_startup=check_updates,
        )


__all__ = ["CURRENT_SETTINGS_OVERLAY_FIELDS", "SettingsRoundTripMixin"]
