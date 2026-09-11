# Current architecture — HappyMeasure 1.1b6

This document owns the current runtime boundaries and invariants. Historical UI/refactor detail belongs in Git history, `CHANGELOG.md`, or versioned release notes.

## Repository applications

The repository contains two user-facing applications with separate UI stacks:

- **HappyMeasure** — Tkinter + Matplotlib measurement application under `src/keith_ivt/`, exposed publicly through the `happymeasure` package/entry point while retaining `keith_ivt` as the compatibility/internal namespace.
- **Map Reconstruction** — optional PySide6 + PyQtGraph application under `src/map_reconstruction/`, installed with `.[map]`.

The applications exchange measurement data through documented file formats. Map Reconstruction must not import HappyMeasure UI, application state, or serial-driver internals.

## HappyMeasure runtime layers

```text
src/keith_ivt/
  models.py                     SweepConfig, SweepPoint, SweepResult
  acquisition.py                Standard/Fast/Custom acquisition policy
  core/sweep_runner.py          measurement execution/timing
  instrument/                   SourceMeter protocol, simulator, Keithley serial backend
  drivers/                      driver-neutral hardware boundary/adapters
  sweeps/                       driver-neutral sweep planning
  services/                     orchestration, preflight and safety services
  data/                         settings, CSV import/export, presets, persistence
  diagnostics/                  UI and hardware diagnostic routines
  utils/thread_safe.py          bounded thread-safe UI/live buffers
  ui/app_state.py               run/connection state model
  ui/simple_app.py              Tk composition root
  ui/*_controller.py            hardware/run/update workflows
  ui/plot_*.py                  plot rendering, controls and optimization
  ui/trace_*.py                 trace table/actions
  ui/settings_*.py              settings review/round-trip actions
```

### State contract

`AppState` is the application-level owner of run and connection semantics. Compatibility properties may bridge legacy code, but new behavior should not create another independent run-state machine.

Worker threads do hardware/timing work and communicate with Tk through the UI queue. Tk widgets are updated on the UI thread.

### Acquisition/safety contract

Validation must complete before source output can be enabled. All success, stop, abort, error, disconnect, and close paths must preserve best-effort `output_off()` cleanup.

Fast acquisition may reduce per-sample overhead, but must not weaken output safety or add per-sample serial queries that erase its timing benefit. A following run starts from deterministic application configuration.

### Queue/rendering contract

The worker may produce points faster than Matplotlib should redraw. Queue processing is bounded and live plotting is throttled independently of acquisition timing.

Time-plot preferences are display policy only:

- marker mode (`Auto` / `On` / `Off`);
- live history (`All data` / `Last N points`);
- refresh interval.

`Last N points` applies to the live Time display path before expensive coordinate preparation. It must never truncate `_live_points`, completed `SweepResult.points`, CSV/project data, or later analysis. Completed large Time traces show the full time range, using extrema-preserving display reduction when needed.

### Settings contract

The active desktop persistence owner in `1.1b6` is the flat dataclass `keith_ivt.data.settings.AppSettings` stored in `config/settings.json`. `sanitize_settings_dict()` supplies backward-compatible coercion/defaults. See `SETTINGS_COMPATIBILITY.md`.

`settings_v2.py` is not the active desktop persistence owner and must not be presented to users as an already-completed migration.

## Map Reconstruction boundary

`src/map_reconstruction/` is an independent optional application. Its core dependency direction is:

```text
UI -> preparation/reconstruction/processing/QC/project IO -> NumPy
```

Qt/PyQtGraph remain optional GUI dependencies. Importers, preparation, numerical reconstruction, processing, project IO and QC should remain headless-testable where practical.

### Three-stage workspace

The UI exposes three explicit stages in a `QStackedWidget`:

1. **Signal Preparation** — source signal selection and time-domain baseline preparation;
2. **Reconstruction** — geometry/registration/reconstruction/QC;
3. **Map Analysis** — post-reconstruction scientific processing and display controls.

Preparation produces a display/reconstruction input without mutating imported source arrays. Reconstruction results remain authoritative raw values; processing/color display state is downstream.

Opening a genuinely new CSV is a workspace replacement operation. The candidate is parsed before the current workspace is discarded. Existing meaningful work receives the Save/Discard/Cancel guard. A successful new-source replacement clears stale reconstruction/analysis state and returns to Stage 1; an invalid/cancelled replacement preserves the old workspace.

### Project contract

`project_io.py` owns the versioned `.hmmap` ZIP/JSON format, embedded original source bytes, metadata and hash verification. Projects reopen from the embedded authoritative source and restore persisted workflow settings; a cached displayed map is not the scientific source of truth.

See `MAP_PROJECT_FORMAT.md` for the archive contract.

### Processing/display contract

Raw reconstructed values, processed values and display scaling are distinct layers:

- raw CSV export writes authoritative reconstruction values;
- processed CSV export writes the scientific processed values plus metadata;
- display-unit scaling and color limits do not overwrite scientific arrays;
- percentile color controls represent distribution percentiles, not percentages of the maximum;
- palette flipping and manual min/max are display controls.

## Extension boundaries

- Hardware-specific SCPI belongs in instrument/driver implementations, not Tk widgets.
- New sweep generation belongs in sweep/planning logic, not UI widgets.
- New persisted settings require backward-compatible defaults and Settings round-trip coverage.
- Public file/schema changes require updates to `TRACE_SCHEMA.md` or `MAP_PROJECT_FORMAT.md` plus compatibility tests.
- UI composition roots should remain small; put behavior in the responsible controller/mixin/module.

See `DRIVER_SWEEP_EXTENSION_GUIDE.md` for driver/sweep extension patterns and `AGENTS.md` for change/safety discipline.

## Release validation boundary

Automated source validation does not equal hardware validation.

- Core HappyMeasure tests run in the Windows Python matrix.
- Map Reconstruction has a dedicated Windows/Python 3.12 offscreen Qt gate that installs real `.[map]` dependencies.
- Portable Windows packaging, desktop visual checks, no-DUT communication checks and dummy-load/real-instrument behavior remain explicit release gates documented in `RELEASE_CHECKLIST.md` and `HARDWARE_VALIDATION_PROTOCOL.md`.
