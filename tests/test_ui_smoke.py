from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def source_text(relative: str) -> str:
    return (SRC / "keith_ivt" / relative).read_text(encoding="utf-8")


def test_ui_split_modules_exist_and_are_wired() -> None:
    app = source_text("ui/simple_app.py")
    nav = source_text("ui/navigation.py")
    status = source_text("ui/status_bar.py")
    mixins = source_text("ui/app_mixins.py")
    assert "from keith_ivt.ui.navigation import NavigationMixin" in mixins
    assert "from keith_ivt.ui.status_bar import StatusBarMixin" in mixins
    assert "from keith_ivt.ui.operator_bar import OperatorBarMixin" in mixins
    assert "class SimpleKeithIVtApp(AppChromeMixin, AppWorkflowMixin, AppPlotTraceMixin)" in app
    assert "UiScaffoldMixin" in mixins and "HardwareControllerMixin" in mixins
    assert "class NavigationMixin" in nav and "def _build_navigation_drawer" in nav
    assert "class StatusBarMixin" in status and "def _build_status_bar" in status


def test_default_page_and_header_status_separation_contract() -> None:
    app = source_text("ui/simple_app.py")
    nav = source_text("ui/navigation.py")
    status = source_text("ui/status_bar.py")
    assert 'self._active_nav = "Hardware"' in app
    assert 'self._show_nav("Hardware")' in app
    assert "self.page_title" in source_text("ui/ui_scaffold.py")
    assert "self.header_status" not in app
    scaffold = source_text("ui/ui_scaffold.py")
    assert "textvariable=self.status_connection_text" not in scaffold
    assert "textvariable=self.status_connection_text" in status
    assert "no longer auto-hides" in nav


def test_live_only_plot_and_trace_list_contract() -> None:
    app = source_text("ui/simple_app.py")
    assert 'self.plot_trace_pane.forget(self.trace_panel)' in source_text("ui/plot_panel.py")
    assert 'traces = [] if getattr(self, "_plot_live_only", False)' in source_text("ui/plot_panel.py")
    assert 'getattr(self, "_run_state", "idle") in {"running", "paused", "stopping"}' in source_text("ui/plot_panel.py")


@pytest.mark.skipif(os.environ.get("HAPPYMEASURE_RUN_TK_SMOKE") != "1", reason="Set HAPPYMEASURE_RUN_TK_SMOKE=1 on a desktop session to run Tk instantiation smoke test")
def test_tk_app_instantiates_default_hardware_page() -> None:
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    try:
        app.root.update_idletasks()
        assert app._active_nav == "Hardware"
        assert app.page_title.cget("text") == "Hardware"
        assert app.status_connection_text.get().startswith("Instrument:")
        assert hasattr(app, "drawer_frame")
        assert hasattr(app, "status_bar")
    finally:
        app.root.destroy()
