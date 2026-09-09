# Map Reconstruction project format

Map Reconstruction projects use the `.hmmap` extension. A project is a ZIP
container with the v1 schema identifier `map-reconstruction-project-v1`.

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

`project.json` stores the selected signal, geometry, Dual Offset registration
using canonical `row_a_s`, `row_b_s`, `point_a_s`, and `point_b_s` fields,
processing configuration in scientific/internal units, and Flip Y display
state. Row and point periods are derived values and are not authoritative
project fields.

Opening a project reads only these known archive members without extraction,
validates the schema and source SHA-256, then imports the embedded raw CSV and
reconstructs it with the current code. SHA-256 mismatch, malformed metadata,
missing members, and unsupported schemas are rejected. This release implements
only v1; future schemas require an explicit migration path.
