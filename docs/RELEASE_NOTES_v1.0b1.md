# HappyMeasure 1.0 beta 1 (`1.0b1`)

HappyMeasure 1.0 beta 1 is the first beta candidate after the alpha hardware smoke-testing phase. The app remains focused on Keithley 2400/2450-style IV workflows with simulator-first validation and manual hardware preflight.

## Highlights

- Public launch namespace: `happymeasure`; legacy compatibility namespace: `keith_ivt`.
- Hardened run-state, Stop/Abort, output-off cleanup, and simulator fault-injection paths.
- Improved CSV/trace round trips, metadata preservation, multi-select trace export, latest-trace selection, and factory-settings restore.
- Refined UI for beta use: compact status bar, signed live V/I/Cmpl readout, Keithley-style front-panel popup, Canvas status indicators, top-title hover summaries, Log restoration, and duplicate-title cleanup.
- Plot improvements: per-view X/Y swap, fullscreen screenshot export, safer layout handling, and current-source IV plots using current on the X-axis.
- Documentation updated for release checklist, manual smoke testing, trace schema, hardware preflight, and namespace migration.

## Validation status

- Simulator/source validation is the release gate for this beta.
- Initial hardware smoke testing has confirmed that the app can measure, but not every hardware feature has been bench-tested.
- Full hardware bench validation is intentionally scheduled after this beta release.

## Manual upgrade behavior

HappyMeasure checks GitHub Releases metadata only. It does not download, install, or replace itself. Users should download and replace the portable folder manually from the GitHub Release page.

## Suggested release asset

```text
HappyMeasure-1.0b1-windows-portable.zip
```
