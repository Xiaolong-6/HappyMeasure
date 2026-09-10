# Built-in UI Diagnostics

HappyMeasure includes a safe UI-only diagnostic runner for reproducing desktop
workflow problems without requiring an external mouse-automation tool.

Open **Settings** and choose **Run UI Diagnostics...**. The dialog immediately
exercises the application's real Tk navigation buttons and live control
callbacks, including repeated Sweep/page navigation, Constant-Time acquisition
profile controls when available, advanced-control show/hide behavior, and
mode-dependent source/measurement range labels.

The UI self-test is intentionally non-hardware-facing. It does **not** invoke
Connect, Start, Pause, Stop, or any instrument command, and it never changes
instrument output. If a measurement is active, the self-test refuses to run. If
measurement traces are already loaded, parameter-mutation checks are skipped so
the diagnostic cannot clear unsaved data.

After each run HappyMeasure writes a shareable ZIP under:

```text
logs/diagnostics/ui_YYYYMMDD_HHMMSS.zip
```

The ZIP contains:

- `summary.json` — machine-readable PASS/FAIL/SKIP results and runtime context;
- `summary.txt` — the same result in operator-readable form;
- `app_log_tail.txt` — a bounded tail of the current application log.

The diagnostic temporarily snapshots the small set of UI variables it changes
and restores them after the run. Connection state is checked before and after
the test. The diagnostic is designed to complement, not replace, native visual
inspection: it can catch stale widgets, callback exceptions, state-restoration
problems, or missing controls, but it cannot decide whether a layout is visually
balanced or aesthetically clear.

Real Keithley validation remains a separate hardware-safety workflow. The
built-in UI diagnostic must not be extended to source voltage/current merely for
convenience; hardware tests should retain an explicit operator safety gate and
`OUTPUT OFF` cleanup contract.
