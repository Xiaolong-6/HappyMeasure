# Next Release Draft

This file is the working release draft. It intentionally does not assign the final public version; the human release owner selects that after the release audit is green.

## HappyMeasure

- Serial discovery is safer: GUI **Detect COM** only enumerates Windows COM ports and never auto-scans baud rates. Connect/model identification uses the operator-selected baud.
- Hardware preflight import-cycle failure is fixed.
- Developer Tools now owns both UI Diagnostics and Hardware Diagnostics; diagnostics buttons remain available after returning to/rebuilding the Settings page.
- Diagnostic explanatory prose was reduced; safety/behavior detail lives in button hover text and owner documentation.
- `Review Default Settings...` no longer crashes when `check_updates_on_startup` has no dedicated live Tk variable.
- Default Settings includes **Auto-save backup** and **Record log**, both enabled by default.
- Automatic backup preference applies to normal completion and partial-result rescue; manual Backup remains available.
- Time plots expose live **All data / Last N points** history controls during acquisition. Display windowing never truncates acquired or exported scientific data.
- Windows launcher remains resilient when bare `python` is missing/Store-aliased and avoids user-specific path examples in tracked source.

## Map Reconstruction

- The staged Signal Preparation → Reconstruction → Map Analysis workflow and standalone package remain part of the release scope.
- Existing package-size hardening is retained, with an automated release ceiling of 180 MiB extracted / 80 MiB ZIP to prevent regression toward the earlier oversized package.

## Automated release packaging

- Pushes to `main` now build both Windows portable applications after the source and Map gates pass.
- The package gate audits structure, privacy, generated debris and Map dependency/size regressions.
- Both frozen executables are smoke-launched on the Windows runner.
- CI generates `release-artifacts.json` with exact ZIP size and SHA-256 values and uploads both audited ZIPs as short-lived workflow artifacts.
- Release artifacts from an older commit are never treated as evidence for a newer commit.

## Validation/evidence scope

- Full release CI must pass on the exact selected commit.
- Existing Keithley MODEL 2401 no-DUT preflight/release-smoke evidence is retained for communication/control/safety behavior.
- No passive-load quantitative accuracy test was performed in the current release-prep session; release wording must not imply otherwise.
- A package rebuild alone does not require another hardware bench session unless hardware I/O/safety behavior changed.

## README screenshots

- Restored the README screenshot surface after it was accidentally removed during documentation consolidation.
- Six screenshots under `docs/screenshots/` are release-controlled documentation assets covering HappyMeasure Hardware/sweep/front-panel views and the three Map Reconstruction workflow stages.
- Any stale captures must be refreshed from the final Windows candidate before publication and must not expose usernames, workstation paths, physical instrument serial numbers or unrelated desktop content.

## Privacy/documentation cleanup

- Removed stale versioned release-note files from the active tree; Git history and `CHANGELOG.md` preserve history.
- Removed workstation-specific absolute paths and physical instrument serial identifiers from tracked tests/docs.
- Added a repository privacy regression and explicit documentation policy against committing those identifiers.
