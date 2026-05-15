# Driver and sweep extension guide

Version: `0.1.19-alpha`

This document explains the new separation between hardware drivers, sweep planning, and measurement execution. It is written for future agents/developers opening a fresh thread.

## Goal

The UI should eventually support several instrument families and measurement families:

- Keithley 2400/2401 and similar SMUs;
- future Keysight/NI/other SMUs;
- IV sweeps;
- fixed-source time traces;
- adaptive/table sweeps;
- future CV and combined IVCV workflows.

The UI must not be the place where hardware-specific SCPI or sweep point generation lives.

## New Python-native architecture

```text
src/keith_ivt/
├─ drivers/              # hardware boundary: instrument capabilities + read/write API
│  ├─ base.py            # SMUDriver protocol, ConnectionProfile, capability dataclasses
│  ├─ simulated_smu.py   # generic IV/CV-capable simulator
│  └─ keithley2400_adapter.py
├─ sweeps/               # driver-neutral sweep plans and value generation
│  ├─ plan.py            # SweepPlan, plan_from_config, make_plan
│  └─ table_sweep.py     # simple Start/Stop/Step segment rows
├─ services/
│  └─ measurement_service.py  # executes SweepPlan with any SMUDriver
├─ instrument/           # legacy compatibility layer used by current UI
├─ core/                 # legacy runner and adaptive helpers
└─ ui/                   # Tk UI; should call services rather than owning hardware logic
```

This is not a direct copy of the MATLAB architecture. It uses Python-style protocols, dataclasses, small functions, and explicit service boundaries.

## Driver boundary

New drivers should implement `keith_ivt.drivers.base.SMUDriver`.

Required core methods:

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

Drivers should expose `capabilities`, for example whether they support:

- voltage source;
- current source;
- CV;
- front/rear terminals;
- 4-wire sense;
- fixed range;
- manual output.

## Sweep boundary

Sweep generation should produce a `SweepPlan`, not manipulate UI widgets.

A `SweepPlan` contains:

- source mode;
- measure mode;
- source values;
- compliance;
- NPLC;
- execution kind;
- optional fixed ranges;
- optional interval;
- metadata;
- warnings.

Existing `SweepConfig` can be converted using:

```python
from keith_ivt.sweeps import plan_from_config
plan = plan_from_config(config)
```

New code should eventually build `SweepPlan` directly.

## Adaptive/table sweep

For the user-facing adaptive sweep, keep the normal path simple:

```text
Start | Stop | Step
```

Each enabled row generates one segment. Adjacent duplicate boundary points are removed. This is implemented in:

```python
keith_ivt.sweeps.table_sweep.values_from_segment_rows
```

Advanced scripted adaptive logic can remain as a developer/debug feature, but it should not be the default UI path.

## Measurement execution

Use:

```python
from keith_ivt.services import MeasurementService
service = MeasurementService(driver)
reads = service.run_plan(plan)
```

This lets the same sweep plan run on:

- simulator;
- Keithley 2400 adapter;
- future SMU drivers.

## Current migration status

- Current UI still uses some legacy `SweepConfig`, `SweepRunner`, and `instrument/*` paths.
- Version `0.1.18-alpha` added the new architecture without forcing a risky UI rewrite; `0.1.19-alpha` is the startup hotfix on top of it.
- Future work should move UI start/pause/stop flows onto `MeasurementService.run_plan()`.

## Adding a new SMU driver

1. Create a new file under `src/keith_ivt/drivers/`, e.g. `keysight_b2900.py`.
2. Implement `SMUDriver` protocol.
3. Add capability metadata.
4. Add a pure simulator or fake test path if hardware is unavailable.
5. Add tests that run a simple `SweepPlan` with the driver or a fake transport.
6. Do not add SCPI directly into UI code.

## Adding CV or IVCV

1. Add capability support in the driver.
2. Add a plan builder that uses `MeasureMode.CAPACITANCE`.
3. Keep CV-specific timing/frequency fields in a plan dataclass or metadata; do not overload IV fields silently.
4. Add simulator outputs for capacitance-vs-bias.
5. Add import/export metadata keys before adding UI buttons.
