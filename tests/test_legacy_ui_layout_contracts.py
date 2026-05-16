from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def source_text(name: str) -> str:
    return (SRC / "keith_ivt" / name).read_text(encoding="utf-8")


def ui_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in (SRC / "keith_ivt" / "ui").glob("*.py"))


def test_version_and_release_contract():
    from keith_ivt import version
    assert version.VERSION == "0.7a1"
    assert "0.7a1" in version.BUILD_NOTE.lower()
    assert 'version = "0.7a1"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_single_bottom_operator_bar_replaces_content_local_controls():
    s = source_text("ui/simple_app.py")
    operator_src = source_text("ui/operator_bar.py")
    scaffold = source_text("ui/ui_scaffold.py")
    assert 'self.action_bar = ttk.Frame(self.content_frame' not in scaffold
    assert 'from keith_ivt.ui.app_mixins import AppChromeMixin, AppWorkflowMixin, AppPlotTraceMixin' in s
    assert 'OperatorBarMixin' in source_text('ui/app_mixins.py')
    assert 'def _build_operator_bar' in operator_src
    operator = operator_src[operator_src.index('def _build_operator_bar'):operator_src.index('def _update_operator_layout')]
    assert 'self.action_bar = ttk.Frame(self.root, style="Operator.TFrame"' in operator
    assert 'self.action_bar.grid(row=1, column=getattr(self, "_workspace_column", 0)' in operator
    assert 'Start' in operator and 'Pause' in operator and 'STOP' in operator
    assert 'Controls' in operator and 'STOP' in operator


def test_pause_hover_warning_mentions_output_remains_on():
    operator = source_text("ui/operator_bar.py")
    assert "Pause holds the current source state" in operator
    assert "does not turn output off" in operator
    assert "Use STOP for output off" in operator


def test_root_rows_have_workspace_operator_and_dedicated_status_contract():
    s = source_text("ui/simple_app.py")
    layout = s[s.index('def _build_layout'):s.index('def _show_plot_more_menu')]
    assert 'self.root.rowconfigure(0, weight=1)' in layout
    assert 'self.root.rowconfigure(1, weight=0)' in layout
    assert 'self.root.rowconfigure(2, weight=0)' in layout
    assert 'self._build_operator_bar()' in layout
    assert 'self._build_status_bar()' in layout
    operator = source_text("ui/operator_bar.py")
    assert 'StatusPill.TLabel' not in operator
    assert 'self.points_text' not in operator
    status = source_text("ui/status_bar.py")
    assert 'class StatusBarMixin' in status
    assert 'def _build_status_bar' in status
    assert 'textvariable=self.status_connection_text' in status
    assert 'textvariable=self.status' in status
    assert 'textvariable=self.points_text' in status
    assert 'textvariable=self.last_save_text' in status


def test_plot_trace_never_overlay_layout_contract():
    plot = source_text("ui/plot_panel.py")
    assert 'self.plot_trace_pane = ttk.PanedWindow' in plot
    assert 'orient="vertical"' in plot
    assert 'self.plot_body = ttk.Frame(self.plot_trace_pane' in plot
    assert 'self.trace_panel = ttk.Frame(self.plot_trace_pane' in plot
    assert 'self.trace_panel = ttk.Frame(self.plot_body' not in plot
    assert 'def _ensure_plot_trace_panes' in plot
    assert 'self.plot_trace_pane.forget(self.trace_panel)' in plot
    assert 'show_trace=not live_only' in plot
    assert 'self.plot_body.bind("<Configure>", lambda _e: self._update_plot_body_layout()' in plot
    assert 'def _update_plot_body_layout' in plot
    assert 'wide = self.plot_body.winfo_width()' not in plot
    assert 'self.trace_panel.grid(row=0, column=1' not in plot


def test_trace_list_is_named_and_column_is_compact():
    s = source_text("ui/simple_app.py")
    assert 'trace_title_text = StringVar(value="Traces (0)")' in source_text('ui/plot_panel.py')
    assert 'text="Right-click columns"' not in s
    assert 'command=self._show_trace_column_menu_from_button' in source_text('ui/plot_panel.py')
    assert '"color": ("Color", 78)' in source_text('ui/plot_panel.py')
    assert '"name": ("Name", 150)' in source_text('ui/plot_panel.py')
    assert '"name": ("Device", 130)' not in source_text('ui/plot_panel.py')


def test_post5_interaction_hotfix_contracts():
    s = source_text("ui/simple_app.py")
    all_ui = ui_text()
    assert 'self._active_nav = "Hardware"' in s
    assert 'self._show_nav("Hardware")' in s
    assert 'Right-click plot for actions' not in s
    assert 'label="Export selected..."' in all_ui
    assert 'label="Import data..."' in all_ui
    assert 'suggested_single_csv_name' in source_text('ui/trace_panel.py') and 'suggested_all_csv_name' in source_text('ui/trace_panel.py')
    assert 'zoom_x = bool(state & 0x0004)' in all_ui
    assert 'zoom_y = not zoom_x' in all_ui
    assert 'pair[1].configure(state="disabled" if (is_auto or not editable) else "normal")' in all_ui
    assert 'def _update_plot_view_layout' in source_text('ui/plot_panel.py')
    assert 'make_touch_menu' in all_ui
    mixins = source_text('ui/app_mixins.py')
    assert 'from keith_ivt.ui.plot_controls import PlotInteractionMixin' in mixins
    assert 'from keith_ivt.ui.trace_controls import TraceInteractionMixin' in mixins


def test_mockup_locked_core_flat_styles():
    s = source_text("ui/simple_app.py")
    styles = source_text("ui/theme.py")
    for style_name in ["Toolbar.TFrame", "Operator.TFrame", "StatusPill.TLabel", "Start.TButton", "Stop.TButton", "ToggleOn.TButton"]:
        assert style_name in styles
    assert 'background=self._palette["forest"], foreground="#FFFFFF"' in styles
    assert 'background=self._palette["danger"], foreground="#FFFFFF"' in styles
    assert 'focusthickness=0' in styles


def test_drawer_navigation_survives_without_recursive_show_nav():
    s = source_text("ui/simple_app.py")
    nav = source_text("ui/navigation.py")
    assert 'class NavigationMixin' in nav
    assert 'Active.Drawer.TButton' in nav
    assert 'builders[name](self.current_content)' in nav
    assert 'self._hide_drawer()' in nav
    assert 'self._show_nav(self._active_nav)' not in nav


def test_existing_plot_context_restore_contracts_survive():
    s = ui_text()
    assert 'label="Save plot image..."' in s
    assert 'label="Export all traces..."' in s
    assert 'menu.add_cascade(label="X unit"' in s
    assert 'menu.add_cascade(label="Y unit"' in s
    assert 'self.backup_tree = ttk.Treeview' in s
    assert 'Import selected' in s
    assert 'Auto source range' in s
    assert 'Auto measure range' in s


def test_settings_review_dialog_uses_local_mousewheel_binding():
    settings_actions = source_text("ui/settings_preset_actions.py")
    assert 'bind_all("<MouseWheel>"' not in settings_actions
    assert "survive dialog close" in settings_actions
    assert "not canvas.winfo_exists()" in settings_actions


def test_statusbar_connection_summary_and_click_outside_drawer():
    s = source_text("ui/simple_app.py")
    assert 'self.status_connection_text = StringVar(value="Instrument: --")' in s
    assert 'self.header_status = ttk.Label(self.page_header, textvariable=self.status_connection_text' not in s
    status = source_text("ui/status_bar.py")
    nav = source_text("ui/navigation.py")
    assert 'textvariable=self.status_connection_text' in status
    assert 'def _close_drawer_on_outside_click' in nav
    assert 'no longer auto-hides' in nav
    assert 'self._refresh_connection_status_from_state()' in ui_text()
    assert 'self.connection_light_label' in status and 'ConnGreen.TLabel' in ui_text() and 'ConnRed.TLabel' in ui_text()


def test_plot_toolbar_is_view_only_and_actions_are_context_menu():
    s = source_text("ui/simple_app.py")
    all_ui = ui_text()
    plot = source_text("ui/plot_panel.py")
    assert 'text="Views"' in plot
    assert 'self.views_frame = ttk.Frame(toolbar' in plot
    assert 'text="Actions"' not in plot
    assert 'command=self._show_plot_more_menu' not in plot
    for text_label, menu_label in [('Autorange', 'Autorange this view'), ('Fullscreen', 'Open fullscreen'), ('Save Plot', 'Save plot image...')]:
        assert f'text="{text_label}"' not in plot
        assert f'label="{menu_label}"' in all_ui
    assert 'Right-click plot for actions' not in plot



def test_plot_panel_initialization_does_not_reference_undefined_or_threshold_wide():
    s = source_text("ui/simple_app.py")
    build = source_text("ui/plot_panel.py")
    update = source_text("ui/plot_panel.py")
    assert 'if wide else' not in build
    assert 'wide = self.plot_body.winfo_width()' not in build
    assert 'wide = self.plot_body.winfo_width()' not in update

def test_bottom_operator_has_no_duplicate_export_or_status():
    operator = source_text("ui/operator_bar.py")
    assert 'Export Last Data' not in operator
    assert 'Controls' in operator
    assert 'StatusPill.TLabel' not in operator
    assert 'textvariable=self.status' not in operator


def test_device_profile_copy_is_model_only():
    s = source_text("ui/simple_app.py")
    panels = source_text("ui/panels.py")
    assert 'Detected device model' in panels
    hw = source_text("ui/hardware_controller.py")
    assert 'def _detected_device_model' in hw
    summary = hw[hw.index('def _capability_summary'):hw.index('def _sweep_capability_note')]
    assert 'Supports: ' not in summary
    assert 'Unavailable: ' not in summary


def test_trace_refresh_uses_current_sweepmode_enum():
    s = source_text("ui/simple_app.py")
    refresh = source_text("ui/trace_panel.py")
    assert 'SweepMode.VOLTAGE_SOURCE' in refresh
    assert 'SweepMode.VOLTAGE else' not in refresh


def test_operator_bar_reflows_on_narrow_windows_without_status_group():
    s = source_text("ui/simple_app.py")
    operator = source_text("ui/operator_bar.py")
    assert 'def _update_operator_layout' in operator
    assert 'narrow = self.root.winfo_width() < 980' in operator
    assert 'controls.grid(row=1, column=0, columnspan=2' in operator
    assert 'status_box.grid' not in operator


def test_post6_animation_constant_and_split_contracts():
    s = source_text("ui/simple_app.py")
    panels = source_text("ui/panels.py")
    runner = source_text("core/sweep_runner.py")
    models = source_text("models.py")
    all_ui = ui_text()
    mixins = source_text('ui/app_mixins.py')
    assert 'from keith_ivt.ui.panels import PanelBuilderMixin' in mixins
    assert 'from keith_ivt.ui.navigation import NavigationMixin' in mixins
    assert 'from keith_ivt.ui.status_bar import StatusBarMixin' in mixins
    assert 'from keith_ivt.ui.operator_bar import OperatorBarMixin' in mixins
    assert 'class SimpleKeithIVtApp(AppChromeMixin, AppWorkflowMixin, AppPlotTraceMixin)' in s
    assert 'HardwareControllerMixin' in mixins and 'SweepControllerMixin' in mixins and 'DataActionMixin' in mixins
    assert 'class PanelBuilderMixin' in panels
    navigation = source_text("ui/navigation.py")
    assert 'def _commit_drawer_width' in navigation and 'self.root.after(12' not in navigation
    assert 'Constant until Stop' in all_ui
    assert 'continuous_time: bool = False' in models
    assert 'config.sweep_kind is SweepKind.CONSTANT_TIME and config.continuous_time' in runner
    assert 'self.plot_trace_pane.forget(self.trace_panel)' in source_text('ui/plot_panel.py')
    assert 'traces = [] if getattr(self, "_plot_live_only", False)' in source_text('ui/plot_panel.py')
    assert 'self.ui_scale_combo = self._combo' in panels
    assert 'ttk.Scale' not in panels
    log = panels[panels.index('def _build_log_panel'):panels.index('def _build_about_panel')]
    assert 'btns.grid(row=0' in log and 'self.log_text.grid(row=1' in log
    assert '"Hardware": ("🔌", "Hardware")' in navigation


def test_alpha4_startup_splitter_restore_contracts():
    theme = source_text("ui/theme.py")
    plot = source_text("ui/plot_panel.py")
    simple = source_text("ui/simple_app.py")
    assert "from tkinter import ttk" in theme
    assert "from keith_ivt.data.settings import load_settings" in theme
    assert 'self.style.configure("Nordic.TPanedwindow"' in theme
    assert '"Horizontal.TScrollbar"' in theme
    assert 'self.plot_trace_pane = ttk.PanedWindow' in plot
    assert 'self._ensure_plot_trace_panes(show_plot=True, show_trace=True)' in plot
    restore_src = source_text("ui/preset_restore_panel.py") + source_text("ui/data_actions.py")
    restore = restore_src[restore_src.index('def _build_restore_panel'):restore_src.index('def refresh_backup_list')]
    assert 'btns.columnconfigure(col, weight=1, uniform="restore_actions")' in restore
    assert '.pack(side="left"' not in restore
    assert 'text="Import"' in restore and 'text="Open"' in restore



def test_alpha5_plot_trace_regression_and_view_toolbar_contracts():
    plot = source_text("ui/plot_panel.py")
    theme = source_text("ui/theme.py")
    assert 'family = PlotPanelMixin._unit_family(label)' in plot
    assert 'SimpleKeithIVtApp._unit_family' not in plot
    assert 'self.canvas_widget.grid_remove()' not in plot
    assert 'show_plot=False' not in plot
    assert 'style="ToolbarInner.TFrame"' in plot
    assert 'self.views_frame.grid(row=0, column=1, sticky="ew")' in plot
    assert 'takefocus=False' in plot
    assert 'ToolbarInner.TFrame' in theme


def test_alpha5_beta_hardening_foundation_files_exist():
    assert 'class AppState' in source_text("ui/app_state.py")
    assert 'class RunState' in source_text("ui/app_state.py")
    assert 'class ConnectionState' in source_text("ui/app_state.py")
    assert 'class ThreadSafeBuffer' in source_text("utils/thread_safe.py")
    assert 'class ThreadSafeXYBuffer' in source_text("utils/thread_safe.py")
    assert (ROOT / "tests" / "test_app_state.py").exists()
    assert (ROOT / "tests" / "test_thread_safe.py").exists()
    assert (ROOT / "docs" / "BETA_ROADMAP.md").exists()

def test_constant_until_stop_runner_stops_by_callback():
    from keith_ivt.core.sweep_runner import SweepRunner
    from keith_ivt.instrument.simulator import SimulatedKeithley
    from keith_ivt.models import SweepConfig, SweepKind, SweepMode

    seen = {"count": 0}

    def on_point(_point, index: int, total: int) -> None:
        assert total == 0
        seen["count"] = index

    def should_stop() -> bool:
        return seen["count"] >= 3

    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=0.01,
        nplc=0.01,
        debug=True,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=0.1,
        continuous_time=True,
        interval_s=0.04,
    )
    with SimulatedKeithley() as inst:
        result = SweepRunner(inst).run(cfg, on_point=on_point, should_stop=should_stop)
    assert len(result.points) == 3

def main() -> None:
    tests = [
        test_version_and_release_contract,
        test_single_bottom_operator_bar_replaces_content_local_controls,
        test_pause_hover_warning_mentions_output_remains_on,
        test_root_rows_have_workspace_operator_and_dedicated_status_contract,
        test_plot_trace_never_overlay_layout_contract,
        test_trace_list_is_named_and_column_is_compact,
        test_post5_interaction_hotfix_contracts,
        test_statusbar_connection_summary_and_click_outside_drawer,
        test_plot_toolbar_is_view_only_and_actions_are_context_menu,
        test_plot_panel_initialization_does_not_reference_undefined_or_threshold_wide,
        test_trace_refresh_uses_current_sweepmode_enum,
        test_operator_bar_reflows_on_narrow_windows_without_status_group,
        test_bottom_operator_has_no_duplicate_export_or_status,
        test_device_profile_copy_is_model_only,
        test_mockup_locked_core_flat_styles,
        test_drawer_navigation_survives_without_recursive_show_nav,
        test_existing_plot_context_restore_contracts_survive,
        test_settings_review_dialog_uses_local_mousewheel_binding,
        test_post6_animation_constant_and_split_contracts,
        test_constant_until_stop_runner_stops_by_callback,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("All HappyMeasure 0.7a1 baseline tests passed.")


if __name__ == "__main__":
    main()


def test_alpha6_plot_trace_splitter_uses_portable_panes_contract():
    plot = source_text("ui/plot_panel.py")
    assert "def _safe_add_plot_trace_pane" in plot
    helper = plot[plot.index("def _safe_add_plot_trace_pane"):plot.index("def _initialize_plot_trace_sash")]
    assert "weight=" not in helper
    assert "self._safe_add_plot_trace_pane(self.plot_body" in plot
    assert "removing it caused a blue empty background" in plot
    assert "show_plot and" not in plot
    assert "self.plot_trace_pane.forget(self.plot_body)" not in plot
    assert "self.plot_trace_pane.forget(self.trace_panel)" in plot
    assert "self.plot_trace_pane.sashpos" in plot
