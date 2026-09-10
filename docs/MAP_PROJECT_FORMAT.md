# Map Reconstruction project format

Map Reconstruction projects use the `.hmmap` extension. A project is a ZIP
container with one of three explicit schema identifiers:

- `map-reconstruction-project-v1` for Legacy Dual Offset without Signal Preparation.
- `map-reconstruction-project-v2` for Dual Offset — Phase Window without Signal Preparation.
- `map-reconstruction-project-v3` when time-domain Signal Preparation is active.

```text
project.hmmap
├── project.json
└── source/raw_timeseries.csv
```

`source/raw_timeseries.csv` is the authoritative original HappyMeasure
`single-v2` CSV byte stream. Saving a project copies those bytes unchanged;
the archive does not store a regenerated source CSV or a cached map. The
project JSON records its SHA-256 and the original filename, but never an
absolute source path.

`project.json` stores the selected signal, geometry, registration, map-processing
configuration in scientific/internal units, and Flip Y display state. Row and
point periods are derived values and are not authoritative project fields.

V1 stores the unchanged Legacy Dual Offset registration, including its
authoritative `point_offset`. V2 stores only canonical Phase Window state:
row/point anchors, row offset and Y phase, X offset and X phase, window mode,
and the active window width. V2 deliberately omits Legacy-only `point_offset`
and does not store endpoint or fallback compatibility metadata.

V3 adds a `preparation` object tied to `source.signal`. It stores the active
time-domain dark-correction mode, constant/manual/rolling parameters, manual
dark regions, response direction, value gate, and output convention. V1 and V2
load with identity preparation, preserving their historical numerical semantics.
Identity preparation continues to save as V1 or V2 so older project semantics
are not rewritten unnecessarily.

A project is a workspace, not a cached result. It may contain geometry that is
not yet set, or an active preparation configuration that currently lacks enough
manual regions/populated rolling bins to reconstruct. Such a project must still
open successfully: the UI restores the saved state, reports the preparation
validation error, and waits for the operator to fix it before reconstruction.
No invalid preparation is allowed to fall back silently to a previous prepared
trace or configuration.

Opening a project reads only the known archive members without extraction,
validates the schema and source SHA-256, then imports the embedded raw CSV and
reconstructs it with the current code when the restored scientific state is
valid. SHA-256 mismatch, malformed metadata, missing members, unsupported
schemas, and signal mismatches are rejected. No schema stores a cached
authoritative map.
