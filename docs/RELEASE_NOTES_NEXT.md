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
- Existing package-size hardening is retained; final package size/hash must be regenerated from the selected release commit rather than copied from an older build record.

## Validation/evidence scope

- Full release CI must pass on the exact selected commit.
- Existing Keithley MODEL 2401 no-DUT preflight/release-smoke evidence is retained for communication/control/safety behavior.
- No passive-load quantitative accuracy test was performed in the current release-prep session; release wording must not imply otherwise.
- Final Windows portable packages still require fresh build/smoke and SHA-256 recording.

## Privacy/documentation cleanup

- Removed stale versioned release-note files from the active tree; Git history and `CHANGELOG.md` preserve history.
- Removed workstation-specific absolute paths and physical instrument serial identifiers from tracked tests/docs.
- Added a repository privacy regression and explicit documentation policy against committing those identifiers.
