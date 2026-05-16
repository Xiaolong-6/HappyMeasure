# Naming Guide

HappyMeasure is the only user-facing product name.

## Current rule

- Product/UI/documentation name: **HappyMeasure**
- Public Python package/CLI namespace: `happymeasure`
- Legacy implementation namespace: `keith_ivt`
- Console scripts: `HappyMeasure`, `happymeasure`, and `happymeasure-preflight`
- Historical names are not used in the UI or current user-facing docs.

## Namespace migration rule

Use `happymeasure` for new public entry points and documentation:

```powershell
python -m happymeasure
python -m happymeasure.hardware_preflight COM3 --baud 9600
python -m happymeasure.diagnostics
```

Keep `keith_ivt` imports working until the implementation package can be renamed safely. Existing tests and modules may continue importing `keith_ivt`; new external-facing scripts should prefer `happymeasure` and may include a fallback to `keith_ivt` where launch robustness matters.

## Do not introduce these names in new text

- SMU-IVCV Studio
- Keith-IVt Python
- Keith-IVt as a product label

## Acceptable wording

Use: "HappyMeasure public package `happymeasure`; legacy compatibility namespace `keith_ivt`."
