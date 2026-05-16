from __future__ import annotations

"""Grouped UI mixins for the HappyMeasure application shell.

The alpha UI is still intentionally mixin-based because the original Tk app was
split from a monolithic prototype.  This module reduces the public inheritance
surface of :class:`SimpleKeithIVtApp` by grouping related mixins into a few
cohesive layers.  Keep feature implementations in their focused modules; use
these groups only as composition boundaries.
"""

from keith_ivt.ui.app_state_bridge import AppStateBridgeMixin
from keith_ivt.ui.data_actions import DataActionMixin
from keith_ivt.ui.hardware_controller import HardwareControllerMixin
from keith_ivt.ui.navigation import NavigationMixin
from keith_ivt.ui.operator_bar import OperatorBarMixin
from keith_ivt.ui.panels import PanelBuilderMixin
from keith_ivt.ui.plot_controls import PlotInteractionMixin
from keith_ivt.ui.plot_panel import PlotPanelMixin
from keith_ivt.ui.preset_restore_panel import PresetRestorePanelMixin
from keith_ivt.ui.settings_preset_actions import SettingsPresetMixin
from keith_ivt.ui.status_bar import StatusBarMixin
from keith_ivt.ui.sweep_config import SweepConfigMixin
from keith_ivt.ui.sweep_controller import SweepControllerMixin
from keith_ivt.ui.theme import ThemeMixin
from keith_ivt.ui.trace_controls import TraceInteractionMixin
from keith_ivt.ui.trace_panel import TracePanelMixin
from keith_ivt.ui.update_controller import UpdateControllerMixin
from keith_ivt.ui.ui_scaffold import UiScaffoldMixin
from keith_ivt.ui.widget_helpers import WidgetHelperMixin


class AppChromeMixin(
    ThemeMixin,
    NavigationMixin,
    StatusBarMixin,
    OperatorBarMixin,
    UiScaffoldMixin,
    WidgetHelperMixin,
    PanelBuilderMixin,
    PresetRestorePanelMixin,
):
    """Visual shell, navigation, reusable widgets, and static panels."""


class AppWorkflowMixin(
    AppStateBridgeMixin,
    SweepConfigMixin,
    HardwareControllerMixin,
    SweepControllerMixin,
    DataActionMixin,
    SettingsPresetMixin,
    UpdateControllerMixin,
):
    """State bridge, sweep/hardware workflow, persistence, and settings actions."""


class AppPlotTraceMixin(
    PlotPanelMixin,
    PlotInteractionMixin,
    TracePanelMixin,
    TraceInteractionMixin,
):
    """Plot rendering and trace-list interaction layer."""


__all__ = ["AppChromeMixin", "AppWorkflowMixin", "AppPlotTraceMixin"]
