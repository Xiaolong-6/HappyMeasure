# New Thread Context

HappyMeasure is a Windows Tkinter + Matplotlib SMU sweep application. `happymeasure` is the public package namespace; `keith_ivt` remains as the legacy implementation namespace for compatibility.

Important current work:

- Manual update reminder reads GitHub release metadata only through `ui/update_controller.py`; it does not download, install, or replace files.
- AppState centralizes run and connection state transitions.
- CSV import/export metadata round trips have been hardened.
- Stop/Abort safety has been hardened so operator stop attempts output-off even when normal-completion settings would leave output enabled.
- Trace selection/export consistency has been hardened: deleting the last trace clears selection, stale selected IDs are repaired, renamed traces export with edited names, Export all includes hidden traces, and Export visible filters them.
- Status-bar connection/debug indicators are Canvas-rendered icons, not emoji glyphs. They follow the user UI scale, but not the selected font family or Windows emoji fallback.
- Start gating has been fixed to allow ready states after a run (`stopped`, `completed`, `aborted`) as well as initial `idle`, preventing repeated simulator starts from appearing unresponsive.
- Fault-injection simulator tests now cover connect/read/non-finite/output-off failure paths before real hardware testing.
- `ui/simple_app.py` has been trimmed back to a composition root; do not move feature logic back into it.

Before release, run the normal tests, update version/release notes, then perform the Windows portable build validation as the final step.

## Current UI/data hardening note

Status-bar connection indicators are Canvas-rendered, not emoji labels. The simulator/debug state is shown as a small Canvas gear. These icons follow UI scale but not the selected font family. Do not reintroduce red/green/devil emoji for these indicators because Windows/Tk can render them through monochrome fallback fonts.


Additional release-hardening context:

- Legacy `config/settings.json` and `config/presets.json` are deliberately tolerant. Corrupt files fall back to defaults, string booleans are parsed safely, and partial presets are sanitized.
- Trace/export schema is documented in `docs/TRACE_SCHEMA.md` and guarded by `tests/test_trace_schema_contract.py`.
- Human validation steps are centralized in `docs/MANUAL_SMOKE_TESTS.md`.
- Real-hardware preflight is documented in `docs/HARDWARE_PREFLIGHT.md`; the CLI prints readable PASS/FAIL output and does not run a sweep.

Documentation cleanup status:

- `docs/README.md` is the documentation index.
- `docs/RELEASE_CHECKLIST.md` is the release-prep source of truth.
- `docs/DOCS_AUDIT.md` records the current docs ownership map and non-blocking cleanup candidates.
- Keep new docs linked from the index; avoid creating orphan handoff files.

Legacy test-contract sync status:

- Stale tests have been aligned with Canvas status indicators, Canvas gear debug indicator, `_normalize_theme()`, and `_should_stop` sleep interruption.
- Non-build pytest contracts pass after this sync.
- The remaining known full-suite failures are packaging/build-oriented and are intentionally deferred to the release/build validation phase.
- External audit quick fixes are mostly addressed: `RunState.RUNNING` is documented/tested as a deprecated alias for canonical `RunState.SWEEPING`, redundant coverage omit configuration was removed, and `docs/MIGRATION_PLAN.md` owns the staged `keith_ivt` -> `happymeasure` migration plan. Coverage/mypy policy changes remain deferred.


## Beta UI polish note

The left navigation rail uses user-facing hover summaries for each tab; keep these concise and task-oriented. The About page must always show a non-empty update status, even before/without a successful update check. Dark-theme About labels should use About-specific card-background styles rather than native/default label backgrounds.
