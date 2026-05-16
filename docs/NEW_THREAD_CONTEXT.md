# New Thread Context

HappyMeasure is a Windows Tkinter + Matplotlib SMU sweep application. `happymeasure` is the public package namespace; `keith_ivt` remains as the legacy implementation namespace for compatibility.

Important current work:

- Manual update reminder reads GitHub release metadata only; it does not download, install, or replace files.
- AppState centralizes run and connection state transitions.
- CSV import/export metadata round trips have been hardened.
- Stop/Abort safety has been hardened so operator stop attempts output-off even when normal-completion settings would leave output enabled.
- Trace selection/export consistency has been hardened: deleting the last trace clears selection, stale selected IDs are repaired, renamed traces export with edited names, Export all includes hidden traces, and Export visible filters them.
- Status-bar connection lights (`🔴`, `🟢`, `😈`) use a fixed color emoji font and should not follow the user-selected UI font size/family.
- Start gating has been fixed to allow ready states after a run (`stopped`, `completed`, `aborted`) as well as initial `idle`, preventing repeated simulator starts from appearing unresponsive.

Before release, run the normal tests, update version/release notes, then perform the Windows portable build validation as the final step.
