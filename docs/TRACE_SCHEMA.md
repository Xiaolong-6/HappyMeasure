# HappyMeasure Trace and CSV Schema

This document is the release-facing contract for HappyMeasure trace data. It is intended for future agents and developers who touch import, export, trace selection, plot visibility, or multi-device support.

## Current schema

Single-trace CSV exports use the metadata schema label:

```text
HappyMeasure CSV v2
```

The file-level CSV wrapper may use `single-v2`, `wide-v2`, or `long-v2`, but the per-trace metadata contract is the same.

## Required metadata fields

Every exported trace should preserve these fields when available:

```text
schema
exported_at
start_time
device_name
operator
mode
sweep_kind
start
stop
step
compliance
nplc
port
baud_rate
terminal
sense_mode
debug
debug_model
output_off_after_run
point_count
constant_value
duration_s
continuous_time
interval_s
autorange
auto_source_range
auto_measure_range
source_range
measure_range
adaptive_logic
data_fingerprint
config_fingerprint
trace_uid
```

`trace_uid` is derived from `config_fingerprint` and `data_fingerprint`. It is used for import de-duplication and must change when either the sweep configuration or numeric data changes.

## Data columns

Single-trace exports use:

```text
Elapsed_s, <source column>, <measured column>
```

The source/measured column names come from `SweepConfig.csv_headers` so voltage-source and current-source sweeps remain explicit.

Combined exports may be wide or long:

- `wide-v2`: shared source axis and source mode; one measured column per trace.
- `long-v2`: heterogeneous source axes or modes; one row per trace point.

## Visibility and export semantics

Trace visibility is a plotting/UI property, not a data-validity property.

- **Export all** includes visible and hidden traces.
- **Export visible** includes only ticked/visible traces.
- **Export selected** exports the explicitly selected trace(s), whether visible or hidden.

Hidden traces must not be deleted or silently excluded from all-data backup/export paths.

## Import expectations

Import should be tolerant of older HappyMeasure alpha files:

- Missing metadata fields should fall back to safe defaults.
- Boolean strings such as `"False"` must not become truthy by accident.
- Unknown future fields should be ignored unless the importer is explicitly updated to use them.
- Imported traces should refresh trace list, plot, device selection, and save/export state consistently.

## Non-goals

CSV schema metadata is not a substitute for raw lab notebooks or instrument logs. It is intended to preserve enough context for plotting, re-import, trace comparison, and release-regression tests.
