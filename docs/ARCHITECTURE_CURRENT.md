# Current architecture — HappyMeasure

This document owns current runtime boundaries and invariants. Historical UI/refactor detail belongs in Git history and the changelog.

## Repository applications

The repository contains one desktop application plus a lightweight static web entry point:

- **HappyMeasure** — Tkinter + Matplotlib measurement application under `src/keith_ivt/`, exposed through the public `happymeasure` package/entry point while retaining `keith_ivt` as the compatibility/internal namespace.
- **HappyMeasure Project Hub** — static files under `web/` that link users to HappyMeasure releases and independently deployed browser analysis tools.

Map Reconstruction and IV Fitter are separate repositories. Their scientific/frontend implementations, dependencies, tests and deployment pipelines are not owned by the HappyMeasure desktop repository.

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

## Web project-hub boundary

`web/` is presentation/navigation only. It may describe HappyMeasure and link to the externally deployed Map Reconstruction and IV Fitter applications, but it must not duplicate their scientific engines or create a second bundled desktop-analysis runtime.

## Extension boundaries

- hardware-specific SCPI belongs in instrument/driver implementations, not Tk widgets;
- sweep generation belongs in planning/core logic, not UI widgets;
- persisted settings require backward-compatible defaults and round-trip tests;
- public HappyMeasure CSV/schema changes require updates to `TRACE_SCHEMA.md` plus compatibility tests;
- composition roots should remain small.

## Release validation boundary

Automated source validation does not equal hardware validation. Core tests, portable packaging and the recorded no-DUT hardware scope are separate evidence layers described in `RELEASE_CHECKLIST.md`, `VALIDATION_STATUS.md` and `HARDWARE_VALIDATION_PROTOCOL.md`.
