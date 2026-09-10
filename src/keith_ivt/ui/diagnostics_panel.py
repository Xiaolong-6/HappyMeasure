from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from keith_ivt.diagnostics.ui_self_test import (
    UiDiagnosticReport,
    run_ui_self_test,
    write_ui_diagnostic_bundle,
)
from keith_ivt.ui.mixin_typing import UiMixinTyping
from keith_ivt.ui.widgets import add_tip


class DiagnosticsUiMixin(UiMixinTyping):
    """Expose a safe built-in UI self-test from the Settings page."""

    def _build_settings_panel(self, parent) -> None:
        super()._build_settings_panel(parent)  # type: ignore[misc]

        box = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        box.pack(fill="x", padx=10, pady=(4, 10))
        box.columnconfigure(0, weight=1)
        ttk.Label(
            box,
            text="Diagnostics",
            style="Card.TLabel",
            font=(
                getattr(self.settings, "ui_font_family", "Verdana"),
                int(getattr(self.settings, "ui_font_size", 10)),
                "bold",
            ),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            box,
            text=(
                "Run the real Tk navigation and control callbacks automatically. "
                "This UI self-test never connects, starts a measurement, or changes instrument output."
            ),
            style="Muted.TLabel",
            wraplength=380,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 8))
        button = ttk.Button(
            box,
            text="Run UI Diagnostics...",
            command=self._show_ui_diagnostics,
            style="Soft.TButton",
        )
        button.grid(row=2, column=0, sticky="ew")
        add_tip(
            button,
            "Automatically exercises page navigation, Constant-Time acquisition controls, "
            "advanced-control callbacks, and mode-dependent labels, then creates a shareable report.",
        )

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


__all__ = ["DiagnosticsUiMixin"]
