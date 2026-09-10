from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import platform
import sys
import traceback
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from keith_ivt.app_config import AppPaths
from keith_ivt.models import SweepKind, SweepMode
from keith_ivt.version import VERSION

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

_MUTATED_VAR_NAMES = (
    "mode",
    "sweep_kind",
    "start",
    "stop",
    "step",
    "hysteresis",
    "constant_value",
    "duration_s",
    "constant_until_stop",
    "interval_s",
    "compliance",
    "nplc",
    "delay_s",
    "auto_source_range",
    "auto_measure_range",
    "source_range",
    "measure_range",
    "acquisition_profile",
    "acquisition_advanced_visible",
)

_INTERNAL_STATE_NAMES = (
    "_last_mode_value",
    "_last_sweep_kind_value",
    "_pre_fast_nplc",
    "_pre_fast_delay_s",
    "_custom_acquisition_snapshot",
    "_last_acquisition_profile",
    "_numeric_entry_defaults",
)


@dataclass(frozen=True)
class UiDiagnosticCheck:
    name: str
    status: str
    detail: str

    def line(self) -> str:
        return f"{self.status} {self.name}: {self.detail}"


@dataclass(frozen=True)
class UiDiagnosticReport:
    created_at: str
    app_version: str
    python: str
    platform: str
    tk_patchlevel: str
    original_page: str
    run_state: str
    connection_state: str
    instrument_idn: str
    checks: tuple[UiDiagnosticCheck, ...]

    @property
    def overall(self) -> str:
        return FAIL if any(check.status == FAIL for check in self.checks) else PASS

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["overall"] = self.overall
        return payload

    def to_text(self) -> str:
        lines = [
            "HappyMeasure UI diagnostics",
            f"created_at: {self.created_at}",
            f"app_version: {self.app_version}",
            f"python: {self.python}",
            f"platform: {self.platform}",
            f"tk_patchlevel: {self.tk_patchlevel}",
            f"original_page: {self.original_page}",
            f"run_state: {self.run_state}",
            f"connection_state: {self.connection_state}",
            f"instrument_idn: {self.instrument_idn or '--'}",
            "",
            *[check.line() for check in self.checks],
            "",
            f"Overall: {self.overall}",
        ]
        return "\n".join(lines) + "\n"


@dataclass
class _UiSnapshot:
    variables: dict[str, Any]
    internals: dict[str, Any]
    plot_views: dict[Any, bool]


def _state_text(value: Any) -> str:
    if value is None:
        return "unknown"
    enum_value = getattr(value, "value", None)
    return str(enum_value if enum_value is not None else value)


def _tk_patchlevel(root: Any) -> str:
    try:
        return str(root.tk.call("info", "patchlevel"))
    except Exception:
        return "unknown"


def _capture_ui_snapshot(app: Any) -> _UiSnapshot:
    app._ensure_acquisition_vars()
    variable_names = (*_MUTATED_VAR_NAMES, *getattr(app, "_ADVANCED_VAR_NAMES", ()))
    variables: dict[str, Any] = {}
    for name in variable_names:
        var = getattr(app, name, None)
        if var is not None and hasattr(var, "get"):
            variables[name] = deepcopy(var.get())

    internals = {
        name: deepcopy(getattr(app, name))
        for name in _INTERNAL_STATE_NAMES
        if hasattr(app, name)
    }
    plot_views = {
        view: bool(var.get())
        for view, var in getattr(app, "plot_view_vars", {}).items()
        if hasattr(var, "get")
    }
    return _UiSnapshot(variables=variables, internals=internals, plot_views=plot_views)


def _restore_ui_snapshot(app: Any, snapshot: _UiSnapshot, original_page: str) -> str | None:
    try:
        # Restore while Sweep-owned widgets are alive.  The temporary preset flag
        # prevents mode/sweep changes from opening data-clear dialogs or applying
        # mode defaults while the original values are being put back.
        app._show_nav("Sweep")
        app.root.update_idletasks()
        old_applying = bool(getattr(app, "_applying_preset", False))
        app._applying_preset = True
        try:
            for name, value in snapshot.variables.items():
                var = getattr(app, name, None)
                if var is not None and hasattr(var, "set"):
                    var.set(value)
            for view, value in snapshot.plot_views.items():
                var = getattr(app, "plot_view_vars", {}).get(view)
                if var is not None:
                    var.set(value)
            for name, value in snapshot.internals.items():
                setattr(app, name, deepcopy(value))
        finally:
            app._applying_preset = old_applying

        # Rebuild the live Sweep widgets once from the restored state, then return
        # to the page the operator was using before diagnostics.
        app._update_units_for_mode()
        app._update_dynamic_sweep_fields()
        app._update_range_state()
        app._update_point_count()
        app._redraw_all_plots()
        target = original_page if original_page in app.nav_buttons else "Hardware"
        app._show_nav(target)
        app.root.update_idletasks()
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def _callback_error_detail(errors: list[str]) -> str:
    if not errors:
        return "No Tk callback exceptions were captured."
    suffix = f" (+{len(errors) - 1} more)" if len(errors) > 1 else ""
    return errors[0] + suffix


def _make_report(
    app: Any,
    *,
    created_at: str,
    original_page: str,
    run_state: str,
    connection_state: str,
    instrument_idn: str,
    checks: list[UiDiagnosticCheck],
) -> UiDiagnosticReport:
    return UiDiagnosticReport(
        created_at=created_at,
        app_version=VERSION,
        python=sys.version.replace("\n", " "),
        platform=platform.platform(),
        tk_patchlevel=_tk_patchlevel(app.root),
        original_page=original_page,
        run_state=run_state,
        connection_state=connection_state,
        instrument_idn=instrument_idn,
        checks=tuple(checks),
    )


def run_ui_self_test(app: Any) -> UiDiagnosticReport:
    """Exercise real Tk page/control callbacks without touching instrument output.

    The built-in diagnostic intentionally avoids Connect, Start, Pause, Stop and
    every hardware command. It uses the actual navigation buttons, Tk variable
    traces, acquisition-profile combobox callback and advanced-control button.
    """

    created_at = datetime.now().isoformat(timespec="seconds")
    original_page = str(getattr(app, "_active_nav", "Hardware"))
    app_state = getattr(app, "app_state", None)
    run_state = _state_text(getattr(app_state, "run_state", None))
    connection_state = _state_text(getattr(app_state, "connection_state", None))
    instrument_idn = str(getattr(app, "_connected_idn", "") or "")
    checks: list[UiDiagnosticCheck] = []

    if bool(getattr(app_state, "is_running", False)):
        checks.append(
            UiDiagnosticCheck(
                "precondition",
                FAIL,
                "A measurement is active. Stop the run before UI diagnostics; no UI state was changed.",
            )
        )
        return _make_report(
            app,
            created_at=created_at,
            original_page=original_page,
            run_state=run_state,
            connection_state=connection_state,
            instrument_idn=instrument_idn,
            checks=checks,
        )

    snapshot = _capture_ui_snapshot(app)
    callback_errors: list[str] = []
    old_report_callback_exception = app.root.report_callback_exception

    def capture_callback_exception(exc_type, exc_value, _exc_tb) -> None:
        detail = "".join(traceback.format_exception_only(exc_type, exc_value)).strip()
        callback_errors.append(detail)

    app.root.report_callback_exception = capture_callback_exception
    datasets_present = bool(getattr(app, "_datasets", None) and app._datasets.all())

    try:
        app._show_nav("Sweep")
        app.root.update_idletasks()
        sweep_alive = bool(app.dynamic_box.winfo_exists())
        checks.append(
            UiDiagnosticCheck(
                "sweep_page_constructs",
                PASS if sweep_alive else FAIL,
                "Sweep page and dynamic-control parent are alive."
                if sweep_alive
                else "Sweep dynamic-control parent is not alive after navigation.",
            )
        )

        if datasets_present:
            checks.append(
                UiDiagnosticCheck(
                    "time_profile_setup",
                    SKIP,
                    "Existing traces are loaded; parameter mutation was skipped to avoid clearing unsaved data.",
                )
            )
        else:
            app.sweep_kind.set(SweepKind.CONSTANT_TIME.value)
            app.root.update_idletasks()
            app.root.update()
            checks.append(
                UiDiagnosticCheck(
                    "time_profile_setup",
                    PASS if app.sweep_kind.get() == SweepKind.CONSTANT_TIME.value else FAIL,
                    "Constant Time was selected through the live Tk variable/callback path.",
                )
            )

        baseline_sweep_children = (
            len(app.dynamic_box.winfo_children())
            if app._active_nav == "Sweep" and app.dynamic_box.winfo_exists()
            else None
        )
        navigation_sequence = (
            "Hardware",
            "Sweep",
            "Settings",
            "Sweep",
            "Preset",
            "Sweep",
            "Restore",
            "Sweep",
            "Log",
            "Sweep",
            "About",
            "Sweep",
        )
        navigation_ok = True
        navigation_detail = "Repeated page navigation completed with live Sweep widgets."
        for page in navigation_sequence:
            button = app.nav_buttons.get(page)
            if button is None:
                navigation_ok = False
                navigation_detail = f"Navigation button {page!r} is missing."
                break
            before_errors = len(callback_errors)
            button.invoke()
            app.root.update_idletasks()
            app.root.update()
            if len(callback_errors) != before_errors:
                navigation_ok = False
                navigation_detail = f"Tk callback failed while opening {page}: {callback_errors[-1]}"
                break
            if getattr(app, "_active_nav", None) != page:
                navigation_ok = False
                navigation_detail = f"Requested {page}, active page is {getattr(app, '_active_nav', None)!r}."
                break
            if page == "Sweep":
                if not app.dynamic_box.winfo_exists():
                    navigation_ok = False
                    navigation_detail = "Sweep returned with a destroyed dynamic-control parent."
                    break
                if baseline_sweep_children is not None and len(app.dynamic_box.winfo_children()) != baseline_sweep_children:
                    navigation_ok = False
                    navigation_detail = "Sweep dynamic-control child count changed across page reconstruction."
                    break
        checks.append(
            UiDiagnosticCheck(
                "navigation_lifecycle",
                PASS if navigation_ok else FAIL,
                navigation_detail,
            )
        )

        if not datasets_present and navigation_ok:
            app._show_nav("Sweep")
            app.sweep_kind.set(SweepKind.CONSTANT_TIME.value)
            app.root.update_idletasks()
            app.root.update()
            combo = getattr(app, "acquisition_profile_combo", None)
            profiles = tuple(str(value) for value in (combo.cget("values") if combo else ()))
            fast_expected = bool(
                not getattr(app, "_connected", False)
                or getattr(app, "debug", None) is not None
                and app.debug.get()
                or getattr(
                    getattr(app, "_active_capabilities", None),
                    "supports_fast_acquisition",
                    False,
                )
            )
            expected_profiles = ("Standard", "Fast", "Custom") if fast_expected else ("Standard",)
            profile_failures: list[str] = []
            for profile in expected_profiles:
                if profile not in profiles:
                    profile_failures.append(f"{profile} missing for this capability")
                    continue
                assert combo is not None
                before_errors = len(callback_errors)
                combo.set(profile)
                combo.event_generate("<<ComboboxSelected>>")
                app.root.update_idletasks()
                app.root.update()
                if app.acquisition_profile.get() != profile or len(callback_errors) != before_errors:
                    profile_failures.append(profile)
            extra_fast = (
                {"Fast", "Custom"} - set(profiles) if not fast_expected else set()
            )
            if tuple(profiles) != expected_profiles and not extra_fast:
                if not profile_failures:
                    profile_failures.append(
                        f"Expected {', '.join(expected_profiles)} "
                        f"but observed {', '.join(profiles) or 'none'}."
                    )
            if fast_expected and "Standard" not in profiles:
                profile_failures.append("Standard missing")
            checks.append(
                UiDiagnosticCheck(
                    "acquisition_profile_callbacks",
                    PASS if not profile_failures else FAIL,
                    f"Available profiles exercised: {', '.join(profiles) or 'none'} "
                    f"(expected {', '.join(expected_profiles)}; "
                    "unsupported Fast being absent is OK)."
                    if not profile_failures
                    else "Profile callback failure: " + ", ".join(profile_failures),
                )
            )

            # Connection-aware advanced-controls handling: while disconnected
            # the sweep UI is correctly read-only and the button is disabled.
            advanced_button = getattr(app, "advanced_acquisition_button", None)
            if advanced_button is None:
                checks.append(
                    UiDiagnosticCheck(
                        "advanced_controls_availability",
                        FAIL,
                        "Advanced acquisition button is missing in Constant Time.",
                    )
                )
                checks.append(
                    UiDiagnosticCheck(
                        "advanced_controls_callback",
                        FAIL,
                        "Advanced acquisition toggle could not be exercised: button missing.",
                    )
                )
            else:
                try:
                    is_disabled = bool(advanced_button.instate(["disabled"]))  # type: ignore[attr-defined]
                except Exception:
                    try:
                        is_disabled = str(advanced_button.cget("state")) == "disabled"  # type: ignore[attr-defined]
                    except Exception:
                        is_disabled = False
                button_state = "disabled" if is_disabled else "normal"
                # Availability check: disconnected => disabled is correct.
                # Connected + idle => enabled is correct.
                expected_disabled = connection_state == "disconnected"
                # Treat any non-disconnected as expecting enabled for the target
                # diagnostic page (Sweep, idle). The callback exercises the real
                # invoke path only when the button is actually enabled.
                availability_ok = is_disabled == expected_disabled
                expected_text = "disabled" if expected_disabled else "enabled"
                checks.append(
                    UiDiagnosticCheck(
                        "advanced_controls_availability",
                        PASS if availability_ok else FAIL,
                        f"connection_state={connection_state}; button_state={button_state} "
                        f"(expected {expected_text}).",
                    )
                )

                # Callback check: drive the safe UI callback regardless of connection.
                start_visible = bool(app.acquisition_advanced_visible.get())
                first_visible: bool | None = None
                second_visible: bool | None = None
                callback_ok = False
                try:
                    if is_disabled:
                        # Disconnected: invoke() is a no-op for disabled ttk buttons,
                        # so exercise the UI-only toggle directly. This sends no SCPI.
                        app._toggle_advanced_acquisition()  # type: ignore[attr-defined]
                        app.root.update_idletasks()
                        first_visible = bool(app.acquisition_advanced_visible.get())
                        app._toggle_advanced_acquisition()  # type: ignore[attr-defined]
                        app.root.update_idletasks()
                        second_visible = bool(app.acquisition_advanced_visible.get())
                    else:
                        advanced_button.invoke()
                        app.root.update_idletasks()
                        first_visible = bool(app.acquisition_advanced_visible.get())
                        advanced_button.invoke()
                        app.root.update_idletasks()
                        second_visible = bool(app.acquisition_advanced_visible.get())
                    toggled = first_visible is not None and first_visible != start_visible
                    restored = second_visible is not None and second_visible == start_visible
                    callback_ok = bool(toggled and restored)
                except Exception as exc:
                    callback_ok = False
                    first_visible = first_visible  # keep captured
                    second_visible = second_visible
                    callback_errors.append(f"{type(exc).__name__}: {exc}")

                if callback_ok:
                    checks.append(
                        UiDiagnosticCheck(
                            "advanced_controls_callback",
                            PASS,
                            f"connection_state={connection_state}; button_state={button_state}; "
                            f"visible {start_visible} -> {first_visible} -> {second_visible}.",
                        )
                    )
                else:
                    checks.append(
                        UiDiagnosticCheck(
                            "advanced_controls_callback",
                            FAIL,
                            f"connection_state={connection_state}; button_state={button_state}; "
                            f"visible {start_visible} -> {first_visible} -> {second_visible}; "
                            f"expected toggle to {not start_visible} then back to {start_visible}.",
                        )
                    )

            app.mode.set(SweepMode.CURRENT_SOURCE.value)
            app.root.update_idletasks()
            current_labels = (
                str(app.source_range_row[0].cget("text")),
                str(app.measure_range_row[0].cget("text")),
            )
            app.mode.set(SweepMode.VOLTAGE_SOURCE.value)
            app.root.update_idletasks()
            voltage_labels = (
                str(app.source_range_row[0].cget("text")),
                str(app.measure_range_row[0].cget("text")),
            )
            labels_ok = current_labels == (
                "Current source range",
                "Voltage measurement range",
            ) and voltage_labels == (
                "Voltage source range",
                "Current measurement range",
            )
            checks.append(
                UiDiagnosticCheck(
                    "mode_dependent_range_labels",
                    PASS if labels_ok else FAIL,
                    f"Current-source labels={current_labels}; voltage-source labels={voltage_labels}.",
                )
            )
        else:
            reason = (
                "Skipped because existing traces are loaded."
                if datasets_present
                else "Skipped because navigation lifecycle failed."
            )
            for name in (
                "acquisition_profile_callbacks",
                "advanced_controls_button",
                "mode_dependent_range_labels",
            ):
                checks.append(UiDiagnosticCheck(name, SKIP, reason))

        checks.append(
            UiDiagnosticCheck(
                "tk_callback_exceptions",
                PASS if not callback_errors else FAIL,
                _callback_error_detail(callback_errors),
            )
        )
    except Exception as exc:
        callback_errors.append(f"{type(exc).__name__}: {exc}")
        checks.append(
            UiDiagnosticCheck(
                "self_test_execution",
                FAIL,
                f"{type(exc).__name__}: {exc}",
            )
        )
    finally:
        restore_error = _restore_ui_snapshot(app, snapshot, original_page)
        app.root.report_callback_exception = old_report_callback_exception
        checks.append(
            UiDiagnosticCheck(
                "ui_state_restore",
                PASS if restore_error is None else FAIL,
                "Original sweep values, acquisition controls, plot views and page were restored."
                if restore_error is None
                else restore_error,
            )
        )

    connection_state_after = _state_text(
        getattr(getattr(app, "app_state", None), "connection_state", None)
    )
    checks.append(
        UiDiagnosticCheck(
            "connection_state_unchanged",
            PASS if connection_state_after == connection_state else FAIL,
            f"Before={connection_state}; after={connection_state_after}. The self-test invokes no connection or output action.",
        )
    )

    return _make_report(
        app,
        created_at=created_at,
        original_page=original_page,
        run_state=run_state,
        connection_state=connection_state,
        instrument_idn=instrument_idn,
        checks=checks,
    )


def write_ui_diagnostic_bundle(
    report: UiDiagnosticReport,
    *,
    root: str | Path | None = None,
) -> Path:
    """Write one shareable ZIP containing UI results and a bounded app-log tail."""

    paths = AppPaths.from_root(root)
    diagnostics_root = paths.logs / "diagnostics"
    diagnostics_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_dir = diagnostics_root / f"ui_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)

    (run_dir / "summary.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "summary.txt").write_text(report.to_text(), encoding="utf-8")

    app_log = paths.logs / "log.txt"
    log_tail = "No application log was found.\n"
    if app_log.exists():
        try:
            text = app_log.read_text(encoding="utf-8", errors="replace")
            log_tail = text[-12000:]
            if log_tail and not log_tail.endswith("\n"):
                log_tail += "\n"
        except OSError as exc:
            log_tail = f"Could not read application log: {exc}\n"
    (run_dir / "app_log_tail.txt").write_text(log_tail, encoding="utf-8")

    zip_path = diagnostics_root / f"ui_{stamp}.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(run_dir.iterdir()):
            archive.write(path, arcname=path.name)
    return zip_path
