# Naming Guide

HappyMeasure is the only user-facing product name.

## Current rule

- Product/UI/documentation name: **HappyMeasure**
- Python package namespace: `keith_ivt`
- Console script: `HappyMeasure`
- Historical names are not used in the UI or current docs.

## Why the package is still `keith_ivt`

The package namespace is kept for import stability during the alpha phase. Renaming the package would touch every module, launcher, test, and user path immediately before real hardware bring-up. Treat `keith_ivt` as an internal implementation detail until a dedicated package-rename release.

## Do not introduce these names in new text

- SMU-IVCV Studio
- Keith-IVt Python
- Keith-IVt as a product label

## Acceptable wording

Use: "HappyMeasure internal package `keith_ivt`" when the implementation namespace matters.
