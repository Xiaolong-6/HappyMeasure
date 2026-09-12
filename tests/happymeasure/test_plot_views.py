from __future__ import annotations

from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui.plot_views import PlotView, xy_for_view


def test_linear_plot_uses_standard_iv_axes_for_current_source() -> None:
    config = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=10.0,
    )
    result = SweepResult(config, [SweepPoint(source_value=1e-3, measured_value=0.76)])

    x, y, xlabel, ylabel, title, y_is_log = xy_for_view(result, PlotView.LINEAR)

    assert x == [1e-3]
    assert y == [0.76]
    assert xlabel == "Current (A)"
    assert ylabel == "Voltage (V)"
    assert title == "V-I curve"
    assert y_is_log is False
