# Driver and sweep extension guide

Applies to the `1.1b6` architecture. This is extension guidance, not a migration timeline.

## Boundary

Hardware-specific SCPI and sweep point generation do not belong in Tk widgets.

```text
src/keith_ivt/
├─ drivers/              # driver-neutral instrument capability/API boundary
├─ sweeps/               # driver-neutral sweep plans/value generation
├─ services/             # measurement/safety orchestration
├─ instrument/           # current SourceMeter implementations and compatibility layer
├─ core/                 # sweep execution/adaptive helpers
└─ ui/                   # Tk composition/controllers
```

The current HappyMeasure UI still uses compatibility paths where needed; new integration work should move toward the driver/service boundaries without bypassing the established safety and data contracts.

## Driver boundary

New generic SMU drivers should implement `keith_ivt.drivers.base.SMUDriver` and expose explicit capabilities.

Typical operations include:

```python
connect(profile)
disconnect()
identify()
reset()
configure_source_measure(...)
set_source(source_mode, value)
read()
output_on()
output_off()
close()
```

Capabilities should describe what the device actually supports (source modes, terminals, 4-wire sense, fixed range, CV, manual output, etc.). UI availability must follow validated capabilities rather than model-name guesses.

Never put device-specific SCPI directly in a UI panel/controller. Hardware identification should use canonical parsers/helpers so diagnostics and acquisition code agree on the connected model.

## Sweep boundary

Sweep generation should produce data/plans rather than manipulate widgets. `SweepConfig` remains the central HappyMeasure measurement configuration and can be converted to driver-neutral planning where supported.

```python
from keith_ivt.sweeps import plan_from_config

plan = plan_from_config(config)
```

Step magnitude is non-negative; Start/Stop determine direction. Adaptive/table segments use the same direction rule.

For the user-facing Adaptive editor, each non-comment line is:

```text
start, stop, step
```

Duplicate-value behavior is an explicit configuration choice. Do not encode hidden cleanup in a widget.

## Constant-Time acquisition

Standard/Fast/Custom acquisition policy is resolved independently of the UI layout. Fast mode is only offered for validated real-instrument contexts; simulator support is a development path, not evidence that another physical model is safe/fast-compatible.

Performance work must preserve:

- deterministic next-run configuration;
- full authoritative measurement data;
- output-off cleanup on success/stop/error/close;
- no extra per-sample serial telemetry unless explicitly enabled;
- acquisition timing independent of plot redraw cadence.

## Adding a driver

1. Implement the driver/protocol boundary and capability metadata.
2. Add fake/simulator transport tests before hardware access.
3. Add canonical identification/capability tests.
4. Exercise connection, configuration, read, stop/error, and `output_off()` cleanup.
5. Add real-hardware validation to `HARDWARE_VALIDATION_PROTOCOL.md` before claiming support.
6. Keep unsupported controls unavailable in the UI rather than allowing a late runtime failure.

## Adding a measurement family

1. Define configuration/data semantics independently of widgets.
2. Add generation/execution logic with headless tests.
3. Define import/export metadata before adding UI actions.
4. Add recovery/output safety tests for hardware-facing paths.
5. Add UI only after the underlying contract is stable.

For CV/IVCV, add explicit capability and configuration fields; do not overload IV fields silently.

## Compatibility

The public product/package is HappyMeasure / `happymeasure`. `keith_ivt` remains the internal/compatibility namespace in this release line. Do not remove compatibility imports without a deliberate versioned decision documented in `NAMING.md` and release notes.
