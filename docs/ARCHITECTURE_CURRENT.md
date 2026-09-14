# Current architecture — HappyMeasure

This document owns current runtime boundaries and invariants. Historical UI/refactor detail belongs in Git history and the changelog.

## Repository applications

The repository contains two user-facing applications:

- **HappyMeasure** — Tkinter + Matplotlib measurement application under `src/keith_ivt/`, exposed through the public `happymeasure` package/entry point while retaining `keith_ivt` as the compatibility/internal namespace.
- **Map Reconstruction** — optional PySide6 + PyQtGraph application under `src/map_reconstruction/`, installed with `.[map]`.

The applications exchange scientific data through documented file formats. Map Reconstruction must not depend on HappyMeasure UI/application state/serial internals.

## HappyMeasure runtime layers

```text
src/keith_ivt/
  models.py                     SweepConfig, SweepPoint, SweepResult
  acquisition.py                Standard/Fast/Custom acquisition policy
  core/sweep_runner.py          measurement execution/timing
  instrument/                   simulator and Keithley serial backend
  drivers/                      driver-neutral hardware adapters
  services/                     orchestration, preflight and safety services
  data/                         settings, CSV IO, presets, backups/logging
  diagnostics/                  UI/hardware diagnostics
  ui/app_state.py               run/connection state model
  ui/simple_app.py              Tk composition root
  ui/*_controller.py            hardware/run/update workflows
  ui/plot_*.py                  plot rendering/interaction
  ui/trace_*.py                 trace table/actions
  ui/settings_*.py              settings review/round-trip
```

### State and safety contract

`AppState` owns run/connection semantics. Worker threads do hardware/timing work and communicate with Tk through the UI queue; Tk widgets remain UI-thread-owned.

Validation should complete before source output can be enabled. Success, Stop, abort/error, disconnect and close paths must preserve best-effort `output_off()` cleanup. Fast acquisition must not add per-sample queries that erase its timing benefit or weaken output safety.

### Queue/rendering contract

Queue draining is bounded and live plotting is throttled independently of acquisition timing.

Time-plot controls are display-only. During an active run the operator may switch between `All data` and `Last N points` and change N. Those changes must affect only rendered data; authoritative acquisition buffers/results/exports remain complete.

### Settings contract

The active persistence owner is the flat `keith_ivt.data.settings.AppSettings` dataclass. Missing fields use defaults and user-editable fields round-trip through Settings. `auto_save_backup` and `record_log` default to enabled.

### Serial discovery contract

The GUI **Detect COM** action only enumerates OS-reported COM ports. It does not send SCPI and never scans baud rates. Connect/model identification uses the user-selected COM + baud. CLI preflight may probe candidate COM ports at one selected baud only.

## Map Reconstruction boundary

`src/map_reconstruction/` is an independent optional application. Its dependency direction is:

```text
UI -> preparation/reconstruction/processing/QC/project IO -> NumPy
```

The UI exposes Signal Preparation → Reconstruction → Map Analysis. Imported source arrays remain authoritative; preprocessing/reconstruction/display layers must not silently overwrite source scientific data.

`project_io.py` owns the versioned `.hmmap` ZIP/JSON format, embedded source bytes, metadata and hash verification.

## Extension boundaries

- hardware-specific SCPI belongs in instrument/driver implementations, not Tk widgets;
- sweep generation belongs in planning/core logic, not UI widgets;
- persisted settings require backward-compatible defaults and round-trip tests;
- public file/schema changes require updates to `TRACE_SCHEMA.md` or `MAP_PROJECT_FORMAT.md` plus compatibility tests;
- composition roots should remain small.

## Release validation boundary

Automated source validation does not equal hardware validation. Core tests, the Map Qt gate, portable packaging and the recorded no-DUT hardware scope are separate evidence layers described in `RELEASE_CHECKLIST.md`, `VALIDATION_STATUS.md` and `HARDWARE_VALIDATION_PROTOCOL.md`.
