# Built-in Diagnostics

HappyMeasure exposes **Run Hardware Diagnostics...** directly under
**Settings > Diagnostics**, always visible. **Run UI Diagnostics...** stays
behind **Settings > Show developer tools**. The developer-tools visibility
switch is independent of **Use debug simulator**: the simulator selects a
backend, while Developer Tools only exposes diagnostic and development
controls.

## UI Diagnostics

Choose **Run UI Diagnostics...** to exercise the application's real Tk
navigation buttons and live control callbacks, including repeated Sweep/page
navigation, Constant-Time acquisition profile controls when available,
advanced-control show/hide behavior, and mode-dependent source/measurement
range labels.

The UI self-test is intentionally non-hardware-facing. It does **not** invoke
Connect, Start, Pause, Stop, or any instrument command, and it never changes
instrument output. If a measurement is active, the self-test refuses to run. If
measurement traces are already loaded, parameter-mutation checks are skipped so
the diagnostic cannot clear unsaved data.

After each run HappyMeasure writes a shareable ZIP under:

```text
logs/diagnostics/ui_YYYYMMDD_HHMMSS.zip
```

The ZIP contains `summary.json`, `summary.txt`, and a bounded
`app_log_tail.txt`. The diagnostic snapshots the small set of UI variables it
changes and restores them after the run.

## Hardware Diagnostics

Choose **Run Hardware Diagnostics...** for a deliberately narrower Level-0
real-instrument check. Before the Run button is enabled, all of the following
must be true:

- **Use debug simulator** is off;
- no HappyMeasure measurement is active;
- the normal Hardware-page connection is disconnected;
- a COM port is selected; and
- the operator explicitly confirms that no DUT or analog test leads are
  connected.

The diagnostic snapshots the selected COM port and baud rate on the Tk thread,
then performs serial work on a background worker. The worker never reads Tk
variables or touches Tk widgets.

Its hardware contract is intentionally conservative:

1. send `OUTPUT OFF` before other instrument actions;
2. query `*IDN?` and accept only the validated Keithley 2400-family identity;
3. query `:OUTP?` and require the instrument to report output off;
4. use the driver's state-preserving short-beep helper;
5. close and reopen the serial connection;
6. verify the same instrument is present and output remains off; and
7. send `OUTPUT OFF` again before releasing each serial session.

It does **not** reset or configure the source meter, issue `READ?`, set a source
value, start a measurement, or enable source output. Software can verify that
the beep command completed, but it cannot hear the instrument; the operator must
manually confirm that exactly one short beep was audible.

The built-in Hardware Diagnostics is a quick communication/output-safety gate.
It does not replace the repository's no-DUT 0 V smoke runner or the staged
hardware validation protocol in `docs/HARDWARE_VALIDATION_PROTOCOL.md`.

## Scope boundary

UI Diagnostics and Hardware Diagnostics intentionally remain separate. A UI
self-test must never gain hardware side effects for convenience, and the
hardware test must retain its explicit operator safety gate and `OUTPUT OFF`
cleanup contract.
