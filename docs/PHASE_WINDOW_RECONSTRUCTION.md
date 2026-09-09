# Dual Offset — Phase Window

Map Reconstruction provides two explicit scientific registrations.

`Dual Offset (Legacy)` is retained unchanged for every v1 project. Its four
anchors determine both periods and the historical pixel reference behavior.

`Dual Offset — Phase Window` separates those roles:

```text
Trow   = (YB - YA) / Rows apart
Tpoint = (XB - XA) / Points apart

row0 = YA - (row offset + Y phase) * Trow
center(r, c) = row0 + r*Trow
             + (X offset + X phase)*Tpoint + c*Tpoint
window(r, c) = [center - W/2, center + W/2)
```

YA/YB and XA/XB are period anchors only. They do not claim to identify a row
start, a stage dwell, or the start of data acquisition. Y phase aligns the row
origin; X offset plus X phase aligns the first acquisition-window center.

The default width is 65% of one point period. A fixed duration is allowed only
when it is positive and no longer than one point period. Every mapped window
must fall inside its row. Samples are selected with the half-open `[start,end)`
convention: an empty window is an invalid pixel (`NaN`, count `0`), never a
nearest-sample substitution.

The trace shows bounded translucent acquisition bands and orange markers for
the samples in displayed bands. The core uses the full map, while display
graphics are decimated for responsiveness. QC reports valid pixels, zero- and
one-sample fractions, median samples/pixel, and P10 samples/pixel.

Projects remain compatible:

- `map-reconstruction-project-v1` always opens as `Dual Offset (Legacy)`.
- `map-reconstruction-project-v2` records Phase Window parameters explicitly.
- Conversion from Legacy is an explicit UI action. It verifies values and
  counts before applying; its compatibility metadata preserves the frozen
  Legacy endpoint inclusion only for that converted project.
