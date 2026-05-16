from __future__ import annotations

from datetime import datetime
import logging
import queue
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, DoubleVar, IntVar, StringVar, Tk, END
from tkinter import font as tkfont, ttk


from keith_ivt.diagnostics import install_tk_exception_logging, log_runtime_error
from keith_ivt.core.adaptive_logic import DEFAULT_ADAPTIVE_LOGIC
from keith_ivt.data.dataset_store import DatasetStore, DeviceTrace
from keith_ivt.data.logging_utils import AppLog
from keith_ivt.data.settings import load_settings
from keith_ivt.models import SenseMode, SweepConfig, SweepKind, SweepMode, SweepResult, Terminal
from keith_ivt.services.update_check import check_github_release
from keith_ivt.ui.plot_views import DEFAULT_PLOT_VIEWS, PlotView
from keith_ivt.ui.app_mixins import AppChromeMixin, AppWorkflowMixin, AppPlotTraceMixin
from keith_ivt.ui.menu_utils import make_touch_menu, popup_menu
from keith_ivt.ui.app_state import AppState
from keith_ivt.ui.app_state_bridge import AppStateBridgeMixin
from keith_ivt.utils.thread_safe import ThreadSafeXYBuffer
from keith_ivt.version import APP_NAME, APP_CODENAME, __build_note__, __release_stage__, __version__


class SimpleKeithIVtApp(AppChromeMixin, AppWorkflowMixin, AppPlotTraceMixin):
    """Three-panel offline-alpha UI for HappyMeasure.

    The historical internal package remains ``keith_ivt`` for import stability,
    but the user-facing product name is HappyMeasure.
    """

    DEFAULT_ADAPTIVE_ROWS = [
        (-10.0, -1.0, 1.0),
        (-1.0, -0.1, 0.1),
        (-0.1, -0.01, 0.01),
        (-0.01, -0.001, 0.001),
        (0.0, 0.0, 1.0),
        (0.001, 0.01, 0.001),
        (0.01, 0.1, 0.01),
        (0.1, 1.0, 0.1),
        (1.0, 10.0, 1.0),
    ]
    UPDATE_OWNER = "Xiaolong-6"
    UPDATE_REPO = "HappyMeasure"
    UPDATE_REPO_URL = "https://github.com/Xiaolong-6/HappyMeasure"
    UPDATE_CHECK_CACHE_SECONDS = 30 * 60

    def __init__(self) -> None:
        self.root = Tk()
        install_tk_exception_logging(self.root)
        self.root.title(f"{APP_NAME} {__version__}")
        self.root.geometry("1360x820")
        self.root.minsize(760, 500)
        self.settings = load_settings()
        self._normalize_ui_font_setting()
        self._init_style()
        self.app_log = AppLog(max_bytes=self.settings.log_max_bytes)
        self.app_state = AppState()
        self._measurement_xy = ThreadSafeXYBuffer(maxsize=10000)
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._datasets = DatasetStore()
        self._last_result: SweepResult | None = None
        self._last_backup_path: Path | None = None
        self._selected_trace_id: int | None = None
        self._tree_item_to_trace: dict[str, int] = {}
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._connected_idn = ""
        self._active_capabilities = self._default_capabilities(connected=False)
        self._active_nav = "Hardware"
        self._last_mode_value = self.settings.default_mode
        self._last_sweep_kind_value = getattr(self.settings, "default_sweep_kind", SweepKind.STEP.value)
        self._axes = []
        self._x_data: list[float] = []
        self._y_data: list[float] = []
        self._live_points = []
        self._live_config: SweepConfig | None = None
        self._update_check_in_progress = False
        self._last_update_check_result: dict[str, str | None] | None = None
        self._last_update_check_timestamp: float | None = None
        self._update_release_url = self.UPDATE_REPO_URL

        # Sweep and metadata variables
        self.mode = StringVar(value=self.settings.default_mode)
        self.sweep_kind = StringVar(value=getattr(self.settings, "default_sweep_kind", SweepKind.STEP.value))
        self.start = DoubleVar(value=self.settings.default_start)
        self.stop = DoubleVar(value=self.settings.default_stop)
        self.step = DoubleVar(value=self.settings.default_step)
        self.constant_value = DoubleVar(value=getattr(self.settings, "default_constant_value", 0.0))
        self.duration_s = DoubleVar(value=getattr(self.settings, "default_duration_s", 10.0))
        self.constant_until_stop = BooleanVar(value=getattr(self.settings, "default_constant_until_stop", False))
        self.interval_s = DoubleVar(value=getattr(self.settings, "default_interval_s", 0.5))
        self.adaptive_logic = StringVar(value=getattr(self.settings, "default_adaptive_logic", DEFAULT_ADAPTIVE_LOGIC))
        self.compliance = DoubleVar(value=self.settings.default_compliance)
        self.nplc = DoubleVar(value=self.settings.default_nplc)
        self.autorange = BooleanVar(value=self.settings.default_autorange)
        self.auto_source_range = BooleanVar(value=self.settings.default_autorange)
        self.auto_measure_range = BooleanVar(value=self.settings.default_autorange)
        self.source_range = DoubleVar(value=self.settings.default_source_range)
        self.measure_range = DoubleVar(value=self.settings.default_measure_range)
        self.device_name = StringVar(value=self.settings.default_device_name)
        self.operator = StringVar(value=self.settings.default_operator)

        # Hardware variables
        self.port = StringVar(value=self.settings.default_port)
        self.baud_rate = IntVar(value=self.settings.default_baud_rate)
        self.terminal = StringVar(value=self._display_terminal(self.settings.default_terminal))
        self.sense_mode = StringVar(value=self._display_sense(self.settings.default_sense_mode))
        self.debug = BooleanVar(value=self.settings.default_debug)
        self.debug_model = StringVar(value=getattr(self.settings, "default_debug_model", "Linear resistor 10 kΩ"))

        # UI/settings variables
        self.ui_font_family = StringVar(value=getattr(self.settings, "ui_font_family", "Verdana"))
        self.ui_font_size = IntVar(value=getattr(self.settings, "ui_font_size", 10))
        self.ui_theme = StringVar(value=getattr(self.settings, "ui_theme", "Light"))
        self.ui_scale_choice = StringVar(value=f"{int(self.ui_font_size.get())} pt")
        self.adaptive_start = DoubleVar(value=0.001)
        self.adaptive_stop = DoubleVar(value=1.0)
        self.adaptive_step = DoubleVar(value=0.001)
        # Adaptive sweep is now a simple segment table: start / stop / step.
        # Each row is converted to standard step values and concatenated.
        self.adaptive_rows: list[dict[str, DoubleVar]] = []
        self._adaptive_advanced_active = False

        # Settings and plot variables
        self.log_max_kb = IntVar(value=max(10, int((self.settings.log_max_bytes + 1023) // 1024)))
        self.log_max_bytes = IntVar(value=self.settings.log_max_bytes)  # legacy/internal mirror
        self.cache_enabled = BooleanVar(value=self.settings.cache_enabled)
        self.cache_interval_points = IntVar(value=self.settings.cache_interval_points)
        self.arrangement = StringVar(value=self.settings.default_plot_layout)
        self.plot_format = StringVar(value="Lines + markers")
        self.plot_number_format = StringVar(value="Auto")
        self.plot_x_unit = StringVar(value="Auto")
        self.plot_y_unit = StringVar(value="Auto")
        self.trace_column_vars: dict[str, BooleanVar] = {
            "show": BooleanVar(value=True),
            "color": BooleanVar(value=True),
            "name": BooleanVar(value=True),
            "operator": BooleanVar(value=True),
            "mode": BooleanVar(value=True),
            "sweep": BooleanVar(value=True),
            "points": BooleanVar(value=True),
            "start": BooleanVar(value=False),
        }
        # 0.1.14 default: only Linear view enabled. Other views stay available above the plot.
        self.plot_view_vars: dict[PlotView, BooleanVar] = {view: BooleanVar(value=(view is PlotView.LINEAR)) for view in PlotView}
        self.plot_view_vars[PlotView.SPARE].set(False)

        # Dynamic labels
        self.start_label = StringVar(value="Start (V)")
        self.stop_label = StringVar(value="Stop (V)")
        self.step_label = StringVar(value="Step (V)")
        self.const_label = StringVar(value="Const value (V)")
        self.compliance_label = StringVar(value="Compliance (A)")
        self.points_text = StringVar(value="Points: -- · Est: --")

        # Status bar variables
        self.status = StringVar(value="Ready")
        self.instrument_status = StringVar(value="Not connected")
        self.version_text = StringVar(value=f"v{__version__}")
        self.backup_text = StringVar(value="Backup: --")  # retained for restore/legacy messages; not shown in the status bar
        self.last_save_text = StringVar(value="Last save: --")
        self.status_connection_text = StringVar(value="Instrument: --")
        self.update_status_text = StringVar(value="")
        self.update_notice_text = StringVar(value="")
        self.connection_light_text = StringVar(value="disconnected")

        self._build_layout()
        self._bind_variables()
        self._show_nav("Hardware")
        self._update_units_for_mode()
        self._update_point_count()
        self._refresh_instrument_indicator()
        self._update_run_button_states()
        self._redraw_all_plots()
        self.log_event("UI ready. Three-panel simulator-first alpha path active.")
        self.root.after(100, self._process_queue)
        self.root.after(500, self._check_for_updates_async)


    def _normalize_ui_font_setting(self) -> None:
        """Use only fonts present on the current system; default to Verdana."""
        try:
            families = set(tkfont.families(self.root))
        except Exception:
            families = set()
        preferred = getattr(self.settings, "ui_font_family", "Verdana") or "Verdana"
        if families and preferred not in families:
            self.settings.ui_font_family = "Verdana" if "Verdana" in families else sorted(families)[0]

    # ------------------------------------------------------------------
    # Style and layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)
        self.root.rowconfigure(2, weight=0)
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self._workspace_column = 1

        # Navigation is a persistent side rail.  Opening it reserves a real
        # grid column so it pushes the workspace right, instead of floating
        # over the panels.
        self._build_navigation_drawer()

        self.main_pane = ttk.PanedWindow(self.root, orient="horizontal", style="Nordic.TPanedwindow")
        self.main_pane.grid(row=0, column=self._workspace_column, sticky="nsew")

        self.content_frame = ttk.Frame(self.main_pane, style="Card.TFrame", width=450)
        self.plot_frame = ttk.Frame(self.main_pane, style="Card.TFrame", width=820)
        self.main_pane.add(self.content_frame, weight=1)
        self.main_pane.add(self.plot_frame, weight=3)

        self._build_content_scaffold()
        self._build_plot_panel()
        self._build_operator_bar()
        self._build_status_bar()

    # ------------------------------------------------------------------
    # Config factory
    # ------------------------------------------------------------------
    def _make_config(self) -> SweepConfig:
        sweep_kind = self._sweep_kind_from_ui()
        if sweep_kind is SweepKind.ADAPTIVE:
            self.adaptive_logic.set(self._adaptive_logic_from_table())
        return SweepConfig(
            mode=self._mode_from_ui(),
            start=float(self.start.get()),
            stop=float(self.stop.get()),
            step=float(self.step.get()),
            compliance=float(self.compliance.get()),
            nplc=float(self.nplc.get()),
            port=self.port.get(),
            baud_rate=int(self.baud_rate.get()),
            terminal=Terminal(self._terminal_scpi(self.terminal.get())),
            sense_mode=SenseMode(self._sense_scpi(self.sense_mode.get())),
            device_name=self.device_name.get().strip() or "Device",
            operator=self.operator.get().strip(),
            debug=bool(self.debug.get()),
            sweep_kind=sweep_kind,
            constant_value=float(self.constant_value.get()),
            duration_s=float(self.duration_s.get()),
            continuous_time=bool(self.constant_until_stop.get()),
            interval_s=float(self.interval_s.get()),
            autorange=bool(self.auto_source_range.get() and self.auto_measure_range.get()),
            auto_source_range=bool(self.auto_source_range.get()),
            auto_measure_range=bool(self.auto_measure_range.get()),
            source_range=float(self.source_range.get()),
            measure_range=float(self.measure_range.get()),
            adaptive_logic=self.adaptive_logic.get() or DEFAULT_ADAPTIVE_LOGIC,
            debug_model=self.debug_model.get(),
        )

    def _show_plot_more_menu(self) -> None:
        menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        layout_menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        for label in ["Auto", "Horizontal", "Vertical"]:
            layout_menu.add_radiobutton(label=label, variable=self.arrangement, value=label, command=self._redraw_all_plots)
        menu.add_cascade(label="Layout", menu=layout_menu)
        menu.add_separator()
        menu.add_command(label="Clear Traces", command=self.clear_all_traces)
        x = self.root.winfo_pointerx(); y = self.root.winfo_pointery()
        popup_menu(menu, x, y)

    def log_event(self, message: str) -> None:
        """Record a user-visible UI event and mirror it to the central app logger."""
        logger = logging.getLogger("keith_ivt.ui.events")
        try:
            line = self.app_log.write(message)
            logger.info(message)
        except Exception as exc:
            logger.error("Failed to write user-visible AppLog event", exc_info=(type(exc), exc, exc.__traceback__))
            line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        if hasattr(self, "log_text") and self.log_text.winfo_exists():
            self.log_text.insert(END, line.replace("] ", "]  ", 1) + "\n")
            self.log_text.see(END)

    def _check_for_updates_async(self) -> None:
        """Start a non-blocking GitHub release metadata check."""
        if self._has_fresh_update_check_result():
            self._handle_update_check_result(self._last_update_check_result, from_cache=True)
            return
        if self._update_check_in_progress:
            return
        self._update_check_in_progress = True
        threading.Thread(target=self._check_for_updates_worker, daemon=True).start()

    def _check_for_updates_worker(self) -> None:
        try:
            result = check_github_release(
                self.UPDATE_OWNER,
                self.UPDATE_REPO,
                __version__,
                include_prerelease=True,
                timeout_s=3.0,
            )
        except Exception as exc:
            result = {
                "status": "error",
                "message": f"Update check unavailable: {exc}",
                "latest_version": None,
                "release_url": None,
            }
        self.root.after(0, lambda result=result: self._handle_update_check_result(result))

    def _has_fresh_update_check_result(self) -> bool:
        if self._last_update_check_result is None or self._last_update_check_timestamp is None:
            return False
        age_s = time.monotonic() - self._last_update_check_timestamp
        return age_s < self.UPDATE_CHECK_CACHE_SECONDS

    def _show_cached_update_check_result(self) -> bool:
        if not self._last_update_check_result:
            return False
        self._handle_update_check_result(self._last_update_check_result, from_cache=True)
        return True

    def _handle_update_check_result(
        self,
        result: dict[str, str | None] | None,
        from_cache: bool = False,
    ) -> None:
        if result is None:
            return
        if not from_cache:
            self._update_check_in_progress = False
            self._last_update_check_result = result
            self._last_update_check_timestamp = time.monotonic()
        status = result.get("status")
        message = result.get("message") or "Update check unavailable."
        release_url = result.get("release_url")
        if release_url:
            self._update_release_url = release_url

        if status == "newer":
            self.update_notice_text.set(message)
            self.update_status_text.set(message)
            if not from_cache:
                self.log_event(message)
        elif status == "offline":
            self.update_notice_text.set("Update check unavailable: offline.")
            self.update_status_text.set("Update check unavailable: offline.")
        elif status == "error":
            self.update_notice_text.set("Update check unavailable.")
            self.update_status_text.set("Update check unavailable.")
            logging.getLogger("keith_ivt.ui.updates").warning(message)
        else:
            self.update_notice_text.set("")
            self.update_status_text.set("")

    def _open_update_release_page(self) -> None:
        try:
            webbrowser.open(self._update_release_url or self.UPDATE_REPO_URL)
        except Exception as exc:
            logging.getLogger("keith_ivt.ui.updates").warning("Failed to open release page: %s", exc)

    def _check_for_updates(self) -> None:
        """Compatibility hook retained for callers that still request a check."""
        self._check_for_updates_async()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    try:
        SimpleKeithIVtApp().run()
    except Exception as exc:
        log_runtime_error("UI main failed", exc)
        raise


if __name__ == "__main__":
    main()
