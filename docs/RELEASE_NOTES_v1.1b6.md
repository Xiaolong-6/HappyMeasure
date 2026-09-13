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

## Hardware and recovery hardening

- Real-driver `OUTPUT OFF` write failures now propagate as errors instead of being silently treated as successful cleanup.
- Hardware preflight now forces `OUTPUT OFF`, queries `:OUTP?`, and requires the instrument to report an off state before passing.
- STOP is documented and presented as a **cooperative** stop. It cannot interrupt serial I/O already in progress; the instrument front panel remains the immediate physical output-off path.
- Closing the application during an active run requests Stop and waits for measurement/output-off cleanup instead of destroying the UI immediately.
- Measurement `READ?` is not automatically retried after timeout, reducing duplicate-read risk and bounding STOP latency.
- The first requested source setpoint is written before `OUTPUT ON`, avoiding a transient at a reset/default setpoint.
- Fixed source ranges now reject a requested source value outside the configured range before a run starts.
- If a measurement fails after points were acquired, HappyMeasure attempts to preserve them as an explicitly partial trace and automatic backup.
- Fast/Custom real-hardware acquisition remains capability-gated. The current release evidence validates Fast acquisition specifically on **Keithley MODEL 2401**; simulator support or a related model name is not treated as hardware validation.

## Reliability and compatibility

- Settings review preserves the `Check Updates on Startup` preference instead of silently falling back to its dataclass default.
- Hardware Diagnostics identifies supported Keithley instruments from the canonical `*IDN?` model field rather than matching model-like numbers elsewhere in the reply.
- Time display windows are view-only; CSV/project/trace data remain authoritative and complete.
- Existing settings JSON, presets, HappyMeasure CSVs, `single-v2` data, `.hmmap` projects and the legacy `keith_ivt` namespace remain supported.
- Each measurement run begins from reset/configuration; Fast post-run cleanup normalizes operator-facing state but does not claim to restore an arbitrary unknown pre-run front-panel configuration.

## Validation status

The audited automated gate on 2026-09-13 passed the Windows Python 3.11–3.14 core matrix and the dedicated Windows/Python 3.12 Map Reconstruction Qt gate. Python 3.14 core coverage reached **95.04%**, above the required 95% threshold.

This is **source-level evidence only**. Desktop/package smoke and staged real-hardware validation remain required before publication.

See `VALIDATION_STATUS.md` for the current source/desktop/hardware gate status.

## Portable artifacts

One `v1.1b6` tag ships two independent portable ZIPs sharing the single `1.1b6` version:

- `HappyMeasure-1.1b6-windows-portable.zip` — acquisition application;
- `MapReconstruction-1.1b6-windows-portable.zip` — standalone offline post-processing companion (no Python, no HappyMeasure install, no instrument required).

Previously measured package sizes/hashes are not final release evidence after source changes. Build both artifacts from the final release commit and record the resulting package size and SHA-256 before publication.
