from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from keith_ivt.diagnostics.hardware_self_test import (
    HardwareDiagnosticReport,
    run_hardware_self_test,
)
from keith_ivt.diagnostics.ui_self_test import (
    UiDiagnosticReport,
    run_ui_self_test,
    write_ui_diagnostic_bundle,
)
from keith_ivt.ui.mixin_typing import UiMixinTyping


class DiagnosticsUiMixin(UiMixinTyping):
    """Dialogs behind Settings "Run UI Diagnostics..." and hardware diagnostics."""

    def _show_ui_diagnostics(self) -> None:
        existing = getattr(self, "_ui_diagnostics_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.deiconify()
                existing.lift()
                return
        except Exception:
            pass

        win = tk.Toplevel(self.root)
        self._ui_diagnostics_window = win
        win.title("HappyMeasure UI Diagnostics")
        win.transient(self.root)
        win.geometry("760x560")
        win.minsize(620, 420)

        outer = ttk.Frame(win, padding=(12, 10))
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer,
            text="UI self-test",
            style="AboutTitle.TLabel",
            font=(
                getattr(self.settings, "ui_font_family", "Verdana"),
                int(getattr(self.settings, "ui_font_size", 10)) + 2,
                "bold",
            ),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text=(
                "Safe UI-only diagnostic. It uses the application's actual Tk controls and callbacks, "
                "but does not Connect, Start, Pause, Stop, or send hardware commands. Existing traces "
                "are preserved; parameter-mutation checks are skipped when traces are loaded."
            ),
            style="Muted.TLabel",
            wraplength=700,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 8))

        result_text = tk.Text(
            outer,
            wrap="word",
            background=self._palette["input"],
            foreground=self._palette["fg"],
            insertbackground=self._palette["fg"],
            relief="solid" if getattr(self, "_theme_high_contrast", False) else "flat",
            borderwidth=1,
        )
        result_text.grid(row=2, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(outer, orient="vertical", command=result_text.yview)
        scroll.grid(row=2, column=1, sticky="ns")
        result_text.configure(yscrollcommand=scroll.set)

        status = tk.StringVar(value="Ready. The test will start automatically.")
        ttk.Label(outer, textvariable=status, style="Muted.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(6, 4)
        )

        buttons = ttk.Frame(outer)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)
        run_button = ttk.Button(buttons, text="Run again")
        copy_button = ttk.Button(buttons, text="Copy result", state="disabled")
        close_button = ttk.Button(buttons, text="Close", command=win.destroy)
        run_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        copy_button.grid(row=0, column=1, sticky="ew", padx=4)
        close_button.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        state: dict[str, UiDiagnosticReport | str | None] = {
            "report": None,
            "bundle": None,
        }
        running = False

        def render(text: str) -> None:
            result_text.configure(state="normal")
            result_text.delete("1.0", "end")
            result_text.insert("1.0", text)
            result_text.configure(state="disabled")
            result_text.see("1.0")

        def copy_result() -> None:
            report = state["report"]
            if not isinstance(report, UiDiagnosticReport):
                return
            try:
                win.clipboard_clear()
                win.clipboard_append(report.to_text())
                status.set("Diagnostic summary copied to the clipboard.")
            except Exception as exc:
                status.set(f"Could not copy result: {exc}")

        def run() -> None:
            nonlocal running
            if running:
                return
            running = True
            run_button.configure(state="disabled")
            copy_button.configure(state="disabled")
            status.set("Running UI diagnostics...")
            render("Running real Tk navigation/control callbacks...\n")
            win.update_idletasks()
            try:
                report = run_ui_self_test(self)
                bundle = write_ui_diagnostic_bundle(report)
                state["report"] = report
                state["bundle"] = str(bundle)
                render(report.to_text() + f"\nDiagnostic bundle: {bundle}\n")
                status.set(
                    f"{report.overall}. Share the ZIP shown at the bottom when requesting diagnosis."
                )
                copy_button.configure(state="normal")
                try:
                    self.log_event(f"UI diagnostics {report.overall}: {bundle}")
                except Exception:
                    pass
            except Exception as exc:
                render(f"UI diagnostics could not complete:\n{type(exc).__name__}: {exc}\n")
                status.set("FAIL. The diagnostic runner itself raised an exception.")
            finally:
                running = False
                run_button.configure(state="normal")

        run_button.configure(command=run)
        copy_button.configure(command=copy_result)
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.after(80, run)

    def _hardware_diagnostic_precondition(self) -> tuple[bool, str]:
        if bool(self.debug.get()):
            return False, "Turn off Use debug simulator first; this test requires the real backend."
        if bool(getattr(self.app_state, "is_running", False)):
            return False, "Stop the active measurement before running hardware diagnostics."
        if bool(getattr(self, "_connected", False)):
            return False, "Disconnect the instrument from the Hardware page before running diagnostics."
        port = str(self.port.get()).strip()
        if not port:
            return False, "Select a COM port on the Hardware page first."
        return True, f"Ready to test {port} at {int(self.baud_rate.get())} baud."

    def _show_hardware_diagnostics(self) -> None:
        existing = getattr(self, "_hardware_diagnostics_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.deiconify()
                existing.lift()
                return
        except Exception:
            pass

        win = tk.Toplevel(self.root)
        self._hardware_diagnostics_window = win
        win.title("HappyMeasure Hardware Diagnostics")
        win.transient(self.root)
        win.geometry("780x620")
        win.minsize(640, 500)

        outer = ttk.Frame(win, padding=(12, 10))
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(5, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer,
            text="Safe real-hardware diagnostic",
            style="AboutTitle.TLabel",
            font=(
                getattr(self.settings, "ui_font_family", "Verdana"),
                int(getattr(self.settings, "ui_font_size", 10)) + 2,
                "bold",
            ),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text=(
                "This Level-0 check opens the selected real Keithley, forces OUTPUT OFF, runs *IDN? "
                "and :OUTP?, sends one state-preserving short beep, closes/reopens the serial port, "
                "and verifies output is still OFF. It never resets/configures the SMU, starts a "
                "measurement, sets a source value, or enables source output."
            ),
            style="Muted.TLabel",
            wraplength=730,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 8))

        context = tk.StringVar(value="")
        ttk.Label(outer, textvariable=context, style="Card.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )

        no_dut = tk.BooleanVar(value=False)
        confirm = ttk.Checkbutton(
            outer,
            text="I confirm no DUT or analog test leads are connected.",
            variable=no_dut,
        )
        confirm.grid(row=3, column=0, sticky="w")
        ttk.Label(
            outer,
            text=(
                "Software can verify that the beep command was accepted, but it cannot hear the instrument. "
                "After the run, manually confirm that exactly one short beep was audible."
            ),
            style="Muted.TLabel",
            wraplength=730,
            justify="left",
        ).grid(row=4, column=0, sticky="ew", pady=(4, 8))

        result_text = tk.Text(
            outer,
            wrap="word",
            background=self._palette["input"],
            foreground=self._palette["fg"],
            insertbackground=self._palette["fg"],
            relief="solid" if getattr(self, "_theme_high_contrast", False) else "flat",
            borderwidth=1,
        )
        result_text.grid(row=5, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(outer, orient="vertical", command=result_text.yview)
        scroll.grid(row=5, column=1, sticky="ns")
        result_text.configure(yscrollcommand=scroll.set)

        status = tk.StringVar(value="Waiting for the no-DUT confirmation.")
        ttk.Label(outer, textvariable=status, style="Muted.TLabel").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(6, 4)
        )

        buttons = ttk.Frame(outer)
        buttons.grid(row=7, column=0, columnspan=2, sticky="ew")
        for col in range(3):
            buttons.columnconfigure(col, weight=1)
        run_button = ttk.Button(buttons, text="Run Safe Hardware Test")
        copy_button = ttk.Button(buttons, text="Copy result", state="disabled")
        close_button = ttk.Button(buttons, text="Close")
        run_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        copy_button.grid(row=0, column=1, sticky="ew", padx=4)
        close_button.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        result_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        state: dict[str, HardwareDiagnosticReport | None] = {"report": None}
        running = False

        def render(text: str) -> None:
            result_text.configure(state="normal")
            result_text.delete("1.0", "end")
            result_text.insert("1.0", text)
            result_text.configure(state="disabled")
            result_text.see("1.0")

        def refresh_ready_state() -> None:
            ok, reason = self._hardware_diagnostic_precondition()
            backend = "DEBUG SIMULATOR" if bool(self.debug.get()) else "REAL HARDWARE"
            context.set(
                f"Backend: {backend}   Port: {self.port.get()}   Baud: {self.baud_rate.get()}"
            )
            enabled = ok and bool(no_dut.get()) and not running
            run_button.configure(state="normal" if enabled else "disabled")
            if not running:
                if not ok:
                    status.set(reason)
                elif not no_dut.get():
                    status.set("Waiting for the no-DUT confirmation.")
                else:
                    status.set(reason)

        def copy_result() -> None:
            report = state["report"]
            if report is None:
                return
            try:
                win.clipboard_clear()
                win.clipboard_append(report.to_text())
                status.set("Hardware diagnostic summary copied to the clipboard.")
            except Exception as exc:
                status.set(f"Could not copy result: {exc}")

        def worker(port: str, baud: int) -> None:
            try:
                report = run_hardware_self_test(port, baud)
            except BaseException as exc:  # keep worker failure off the Tk thread
                result_queue.put(("error", f"{type(exc).__name__}: {exc}"))
            else:
                result_queue.put(("report", report))

        def poll_result() -> None:
            nonlocal running
            try:
                kind, payload = result_queue.get_nowait()
            except queue.Empty:
                try:
                    if win.winfo_exists() and running:
                        win.after(80, poll_result)
                except Exception:
                    pass
                return

            running = False
            if kind == "report" and isinstance(payload, HardwareDiagnosticReport):
                state["report"] = payload
                render(payload.to_text())
                copy_button.configure(state="normal")
                status.set(
                    f"{payload.overall}. Confirm manually that exactly one short beep was audible."
                )
                try:
                    self.log_event(
                        f"Hardware diagnostics {payload.overall}: "
                        f"{payload.port} / {payload.instrument_idn or '--'}"
                    )
                except Exception:
                    pass
            else:
                render(f"Hardware diagnostics could not complete:\n{payload}\n")
                status.set("FAIL. The hardware diagnostic runner raised an exception.")
            refresh_ready_state()

        def run() -> None:
            nonlocal running
            ok, reason = self._hardware_diagnostic_precondition()
            if running:
                return
            if not ok:
                status.set(reason)
                return
            if not bool(no_dut.get()):
                status.set("Confirm that no DUT or analog test leads are connected.")
                return

            # Snapshot Tk values before starting the worker. The worker never
            # reads Tk variables or touches widgets.
            port = str(self.port.get()).strip()
            baud = int(self.baud_rate.get())
            state["report"] = None
            running = True
            copy_button.configure(state="disabled")
            run_button.configure(state="disabled")
            status.set("Running safe hardware diagnostics...")
            render(
                "Running communication/output-off checks. Source output will not be enabled.\n"
            )
            threading.Thread(
                target=worker,
                args=(port, baud),
                name="happymeasure-hardware-diagnostics",
                daemon=True,
            ).start()
            win.after(80, poll_result)

        def close_window() -> None:
            if running:
                messagebox.showwarning(
                    "Hardware diagnostics",
                    "Wait for the hardware diagnostic to finish before closing this window.",
                    parent=win,
                )
                return
            win.destroy()

        confirm.configure(command=refresh_ready_state)
        run_button.configure(command=run)
        copy_button.configure(command=copy_result)
        close_button.configure(command=close_window)
        win.protocol("WM_DELETE_WINDOW", close_window)
        render(
            "No hardware commands have been sent. Confirm the no-DUT condition to enable the test.\n"
        )
        refresh_ready_state()


__all__ = ["DiagnosticsUiMixin"]
