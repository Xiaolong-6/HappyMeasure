# Release Notes — HappyMeasure 1.1b6

**Release-candidate notes. Do not mark hardware-verified until the final operator gate is completed.**

HappyMeasure 1.1b6 focuses on long-running acquisition usability, Map Reconstruction workflow maturity, diagnostics, and release hardening.

## User-facing changes

- **Smoother Time monitoring:** live Time display can use a bounded recent-point window, configurable marker behavior, and controlled refresh cadence without discarding acquired data. Completed large traces retain the full measurement range and use display-only reduction when needed.
- **Fast Constant-Time acquisition:** Standard/Fast/Custom profiles expose validated acquisition controls while unsupported real instruments remain on Standard behavior.
- **Cleaner Settings and diagnostics:** developer controls are grouped explicitly; UI Diagnostics is simulator/UI-only, while Hardware Diagnostics has an explicit no-DUT safety gate and never enables source output.
- **Better export names:** underscore-containing trace/device names and Time/Adaptive metadata no longer generate duplicated filename fragments.
- **Staged Map Reconstruction:** Signal Preparation, Reconstruction and Map Analysis are separate workflow stages. Opening a new CSV replaces the previous source coherently, `.hmmap` projects remain self-contained, and the standalone window starts maximized.
- **Map analysis controls:** manual color limits, data min/max shortcuts, percentile wording and palette flipping are explicit display controls.

## Reliability and compatibility

- Settings review now preserves the `Check Updates on Startup` preference instead of silently falling back to its dataclass default.
- Hardware Diagnostics identifies supported Keithley instruments from the canonical `*IDN?` model field rather than matching model-like numbers elsewhere in the reply.
- Time display windows are view-only; CSV/project/trace data remain authoritative and complete.
- Existing settings JSON, presets, HappyMeasure CSVs, `single-v2` data, `.hmmap` projects and the legacy `keith_ivt` namespace remain supported.
- Each measurement run begins from reset/configuration; Fast post-run cleanup normalizes operator-facing state but does not claim to restore an arbitrary unknown pre-run front-panel configuration.

## Validation changes

- CI keeps the normal Windows Python 3.11–3.14 source matrix.
- A dedicated Windows/Python 3.12 Map Reconstruction job installs `.[dev,map]`, requires PySide6/pyqtgraph and runs the offscreen Qt release gate.
- Version metadata is advanced to `1.1b6`; the already-published `v1.1b5` release is not reused.

See `VALIDATION_STATUS.md` for the current source/desktop/hardware gate status. Package size, SHA-256 and final hardware status must be filled from the actual release artifact before publication.

## Portable artifacts

One `v1.1b6` tag ships two independent portable ZIPs sharing the single `1.1b6` version: `HappyMeasure-1.1b6-windows-portable.zip` for acquisition and `MapReconstruction-1.1b6-windows-portable.zip` for standalone offline post-processing (no Python, no HappyMeasure install, no instrument required).
