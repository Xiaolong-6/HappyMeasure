"""Close the persistence gap between live Tk settings and ``AppSettings``.

``SettingsPresetMixin`` predates several application-level settings and builds
an ``AppSettings`` snapshot explicitly.  Keep the compatibility overlay small
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
        return replace(
            base,
            check_updates_on_startup=bool(self.check_updates_on_startup.get()),
        )


__all__ = ["CURRENT_SETTINGS_OVERLAY_FIELDS", "SettingsRoundTripMixin"]
