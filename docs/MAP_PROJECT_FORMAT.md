# Map Reconstruction project format

Map Reconstruction projects use the `.hmmap` extension. A project is a ZIP
container with one of two explicit schema identifiers:

- `map-reconstruction-project-v1` for Legacy Dual Offset.
- `map-reconstruction-project-v2` for Dual Offset — Phase Window.

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

`project.json` stores the selected signal, geometry, registration, processing
configuration in scientific/internal units, and Flip Y display state. Row and
point periods are derived values and are not authoritative project fields.

V1 stores the unchanged Legacy Dual Offset registration, including its
authoritative `point_offset`. V2 stores only canonical Phase Window state:
row/point anchors, row offset and Y phase, X offset and X phase, window mode,
and the active window width. V2 deliberately omits Legacy-only `point_offset`
and does not store endpoint or fallback compatibility metadata.

Opening a project reads only these known archive members without extraction,
validates the schema and source SHA-256, then imports the embedded raw CSV and
reconstructs it with the current code. SHA-256 mismatch, malformed metadata,
missing members, and unsupported schemas are rejected. Neither schema stores a
cached authoritative map.
