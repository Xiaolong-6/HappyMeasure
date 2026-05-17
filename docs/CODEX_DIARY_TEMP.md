## 2026-05-17 release prep

- Prepared simple `1.0b1` / `1.0 beta 1` beta version metadata.
- Updated `src/keith_ivt/version.py`, `pyproject.toml`, README, changelog, release checklist, docs index, and current beta release notes.
- Kept build validation as the next step after this version/release-notes commit.
- Hardware bench coverage remains post-release follow-up; simulator/source validation and manual UI smoke checks are the beta release gate.

## 2026-05-17 export-selected and settings factory restore
- Fixed trace context-menu `Export selected...` so a multi-row Treeview selection exports all selected traces into one metadata-preserving combined CSV; single selection still exports one normal CSV.
- Added a `Restore factory settings` button to the Default Settings dialog. The button resets dialog fields to built-in `AppSettings()` defaults and checks those fields; values are not persisted until `Save Selected` is clicked.
- Added source-contract tests for multi-selected trace export and the factory-settings restore button.

## 2026-05-17 duplicate title/log/About cleanup
- Removed duplicate in-panel tab titles; the fixed top-bar title is now the only visible page title.
- Added/kept tab hover summaries on the fixed top-bar title instead of duplicate panel headings.
- Removed the `Named presets` LabelFrame title and the Preset/Restore inline info rows/buttons.
- Moved the About release-stage text into the body copy instead of showing a separate status line.
- Restored Log panel layout by avoiding mixed pack/grid title widgets inside grid-based pages.
- Added regression coverage for duplicate-title and inline-info cleanup.

## 2026-05-17 follow-up UI/status/plot patch
- Removed preset/restore inline info rows and pushed the explanation back into hover tips via the page title + in-panel section title hover.
- Moved points/estimate into the Controls heading (`Controls (xx pts, yy sec)` / continuous variant).
- Added compact live status readout (`Vsrc/Isrc`, `Imeas/Vmeas`, `Cmpl`) with signed engineering-format values and a double-clickable Keithley-style front-panel popup.
- Added fullscreen plot `Save screenshot...` button.
- Tight-layout warning path replaced with constrained-layout/safe fallback.
- Plot X/Y swap now targets only the current plot view from the context menu.
- Current-source default linear/log IV plots now use current on the X axis.
- Range Auto buttons stay editable in idle/stopped/completed states (not only literal `idle`).
- Trace visibility column now shows ☑/☐ and completed sweeps auto-select the newest trace.
- Added source-text + logic contract tests for controls header, front-panel hooks, current-source X-axis default, and plot swap/fullscreen save hooks.

# Codex Diary (Temporary)

This temporary diary records changes made during Codex-assisted turns so release notes can be prepared later.

## 2026-05-16

### Public package namespace migration

- Promoted runtime `PACKAGE_NAME` from the legacy `keith_ivt` namespace to the public `happymeasure` namespace.
- Added `src/happymeasure` command wrappers for `python -m happymeasure`, `python -m happymeasure.hardware_preflight`, and `python -m happymeasure.diagnostics`.
- Kept the existing `keith_ivt` implementation package and imports as a compatibility layer, so old imports and fallback launch paths continue to work.
- Updated Windows launchers, PyInstaller entry points, README/docs, and namespace tests to prefer `happymeasure` while preserving `keith_ivt` fallback behavior.

### Stop / Abort / Pause safety hardening

- Hardened `SweepRunner` so an operator stop attempts `output_off()` even when `output_off_after_run=False`.
- Preserved the existing normal-completion behavior: a successful full sweep still respects `output_off_after_run=False`.
- Added safe output-off error handling so a failed output-off command does not hide the original measurement exception.
- Applied the same output-off error-preservation pattern to the newer `MeasurementService` boundary.
- Added `tests/test_sweep_safety.py` covering operator stop, normal completion, measurement exception cleanup, and output-off failure context.
- Added/updated agent-facing handoff context for the safety contract.

### Trace/export consistency and status-light polish

- Hardened trace selection cleanup so deleting or externally removing the selected trace cannot leave `_selected_trace_id` pointing at a missing trace.
- Added regression tests for deleting the last trace, stale selected trace IDs, rename/export name preservation, and hidden-vs-visible export semantics.
- Documented that Export all includes hidden traces while Export visible filters to ticked traces.
- Replaced status-bar emoji lamps with UI-scale-aware Canvas-rendered connection/debug indicators independent of the selected font family and Windows emoji fallback.

### Simulator start-state regression fix

- Fixed a Start-button regression where the worker was only allowed to start from the strict `idle` state even though the centralized AppState and button-state logic treat `stopped`, `completed`, and `aborted` as ready states.
- Added a regression check so simulator runs can be started again after a completed/stopped/aborted run without restarting the app.
### Trace/export, simulator start, and Canvas status icons

- Hardened trace selection/export consistency and preserved renamed trace names in export paths.
- Fixed simulator Start gating so ready states such as stopped/completed/aborted can start a new sweep.
- Replaced emoji status lamps with UI-scale-aware Canvas indicators and a Canvas gear for simulator/debug mode to avoid Windows/Tk emoji fallback rendering.

### Fault-injection simulator and error-path hardening

- Added deterministic `SimulatorFaultProfile` hooks to the debug simulator for connect, reset/configure, output-on/off, set-source, read, NaN, and Inf fault paths used by tests.
- Hardened `SweepRunner` and `MeasurementService` to reject non-finite source/measurement readbacks before they enter datasets.
- Confirmed error paths still attempt safety `output_off()` and preserve the original measurement/readback error when output-off also fails.
- Aligned `AppState.can_start_sweep()` with UI Start gating so aborted-but-connected runs are restartable.
- Added `tests/test_fault_injection_safety.py` covering simulator connect/read/non-finite faults, driver-service non-finite faults, output-off error preservation, and aborted-state restart gating.

### Simple app composition-root size control

- Extracted the non-blocking GitHub release reminder UI wiring from `ui/simple_app.py` into `ui/update_controller.py`.
- Wired `UpdateControllerMixin` through `AppWorkflowMixin` so `SimpleKeithIVtApp` keeps the same public inheritance surface.
- Reduced `ui/simple_app.py` from 381 lines / 15 function definitions to 290 lines / 8 function definitions, satisfying the engineering baseline contract.
- Updated update-check and engineering-baseline tests to assert the new composition boundary.

### P1 release-hardening pass

- Hardened legacy flat settings loading/saving so corrupt files, unknown fields, string booleans, invalid numbers, old theme names, and `FRONT`/`FRON` terminal spelling differences fall back safely instead of blocking UI startup.
- Hardened sweep preset loading so partial/legacy presets are sanitized with the same compatibility rules and invalid preset entries are ignored.
- Added `docs/TRACE_SCHEMA.md` to formalize the HappyMeasure CSV v2 metadata contract and Export all / Export visible / Export selected semantics.
- Added `docs/MANUAL_SMOKE_TESTS.md` with simulator state-flow, trace/export, config/preset, update-reminder, and hardware-preflight checks for human validation.
- Added `docs/HARDWARE_PREFLIGHT.md` and improved the hardware preflight CLI so ordinary failures print readable PASS/FAIL output instead of a traceback.
- Updated `docs/RELEASE_CHECKLIST.md` and README with focused release-hardening checks.
- Added tests for settings/preset compatibility, trace schema contract, and hardware preflight CLI PASS/FAIL behavior.

### Documentation system audit and release checklist consolidation

- Audited the `docs/` tree, top-level README links, handoff notes, and release-prep documents.
- Expanded `docs/RELEASE_CHECKLIST.md` into the release-prep owner document covering source hygiene, version/naming consistency, documentation audit, source validation, manual smoke checks, hardware gates, version bump, Windows portable packaging, Git/GitHub Release, and post-release verification.
- Reworked `docs/README.md` into a structured documentation index so user, hardware, build, architecture, and agent-facing docs have clear ownership.
- Added `docs/DOCS_AUDIT.md` to record the current documentation ownership map and non-blocking cleanup candidates.
- Added documentation contract tests for release-checklist section coverage and docs index links.

### Legacy test-contract synchronization

- Updated stale legacy UI/source contract tests after the Canvas status-icon, theme-sanitizer, and interruptible-stop refactors.
- Replaced obsolete assertions for `ConnGreen.TLabel` / `ConnRed.TLabel`, the devil emoji debug icon, and direct `should_stop` sleep calls with current Canvas/status-gear and `_should_stop` contracts.
- Full pytest now fails only on two Windows build/packaging contract tests intentionally deferred to the release/build validation phase.
- External audit items from `HappyMeasureClone-Issues.md` were queued as follow-up targets: RunState alias clarity, pyproject coverage cleanup, namespace migration-plan documentation, and coverage/type-check policy review.

### External audit quick fixes

- Clarified `RunState.RUNNING` as a deprecated compatibility alias for canonical `RunState.SWEEPING`; added `RunState.from_legacy_text()` for display/persisted legacy strings such as `running`.
- Removed the redundant `src/happymeasure/diagnostics/*` coverage omit entry because `src/happymeasure/*` already covers the wrapper namespace.
- Added `docs/MIGRATION_PLAN.md` to document the staged `keith_ivt` -> `happymeasure` namespace migration strategy.
- Recorded strict mypy and coverage-threshold changes as deferred engineering-policy decisions rather than next-release blockers.

### Beta UI polish and hover-text audit

- Updated the navigation subtitle to the user-facing copy `Your lab buddy` and added panel-specific hover summaries for every left-rail tab.
- Adjusted status-bar Canvas connection/debug icons so they scale with the UI scale while staying independent of emoji/font-family fallback.
- Improved dark-theme About rendering with About-specific label styles on the card background and a non-empty default update-status message.
- Refined update-status copy so offline/error/current/not-checked states always give the user an actionable manual-release-page path.
- Improved disabled-control theme colors so disabled sweep entries/buttons remain readable in Dark mode without looking like native grey patches.
- Added source-contract tests for beta UI polish, dark About styling, status-icon scaling, and tab tooltip summaries.
