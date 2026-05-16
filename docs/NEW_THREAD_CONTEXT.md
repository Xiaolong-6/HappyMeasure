# New Thread Context

HappyMeasure is a Windows Tkinter + Matplotlib SMU sweep application. `happymeasure` is the public package namespace; `keith_ivt` remains as the legacy implementation namespace for compatibility.

Important current work:

- Manual update reminder reads GitHub release metadata only; it does not download, install, or replace files.
- AppState centralizes run and connection state transitions.
- CSV import/export metadata round trips have been hardened.
- Stop/Abort safety has been hardened so operator stop attempts output-off even when normal-completion settings would leave output enabled.

Before release, run the normal tests, update version/release notes, then perform the Windows portable build validation as the final step.
