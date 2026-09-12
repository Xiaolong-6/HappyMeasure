# Changelog

This file is intentionally concise. Detailed historical notes remain in versioned `RELEASE_NOTES_*.md` files and Git history.

## 1.1b6 — Time acquisition, Map Reconstruction, diagnostics and release hardening

- Added live-only Time plot history/marker/refresh policies, stable rolling axes and extrema-preserving full-range display for large completed traces without truncating authoritative data.
- Added validated Standard/Fast/Custom Constant-Time acquisition profiles and related provenance/throughput controls.
- Added Windows power-guard and safe hardware/UI diagnostics with explicit output-off/no-DUT semantics.
- Reorganized Settings/developer controls and fixed update-check preference round-trip.
- Fixed automatic export naming for underscore-containing trace names and duplicated Time/Adaptive metadata.
- Added staged Signal Preparation → Reconstruction → Map Analysis workflow, processing/color controls, self-contained `.hmmap` projects and coherent new-source replacement.
- Added a dedicated Windows/Python 3.12 offscreen Qt Map Reconstruction CI release gate.
- Added a standalone MapReconstruction portable build sharing the single `1.1b6` version (no Python/HappyMeasure/instrument required).
- Advanced release identity to `1.1b6`; `v1.1b5` remains the previous published beta.

## 1.1b5 — Sweep direction and recovery hardening

- Step and Adaptive step values became magnitudes; Start/Stop determine direction.
- Added canonical preflight validation for active sweep values and non-finite input.
- Made runtime sweep errors recover to a reusable connected state while preserving output-off safety.

## 1.1b4 — Adaptive editor and exact presets

- Added multiline Adaptive segment editing and duplicate-value control.
- Presets restore visible Hardware + Sweep state accurately.
- Fixed retry-at-same-setpoint behavior after range-change discard and several settings/import robustness issues.

## 1.1b3 — Front-panel range control

- Added current autorange/fixed-range control, settling/discard behavior and front-panel range status.
- Added associated Keithley range-query and timing regressions.

## 1.1b2 — Hysteresis sweep beta

- Added optional forward/reverse Step and Adaptive sweeps without duplicating the turn point.
- Preserved hysteresis metadata through CSV import/export.

## 1.1b1 — Startup updater beta

- Added startup update checking and verified portable-update handoff.
- Added plot panning/hover readout, auto-open front panel and per-point Delay control.

## 1.0b1 — Beta baseline

- Consolidated HappyMeasure public naming and compatibility namespace.
- Hardened state/recovery/output-off behavior and core trace workflows.

## Earlier alpha history

See Git tags/history and `RELEASE_NOTES_v0.7a1.md` for the pre-beta architecture and hardware-validation transition.
