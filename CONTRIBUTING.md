# Contributing

HappyMeasure is hardware-facing software. Code changes are not complete until
the operator-facing documentation is checked.

## Documentation Rule

Every change must do one of these before it is committed:

- Update the relevant documentation.
- Add a release-note or checklist entry.
- Explicitly decide that no documentation change is needed, and say why in the
  commit message, pull request, or handoff note.

This applies especially to:

- Hardware behavior, safety behavior, Pause/STOP semantics, output state, and
  compliance handling.
- Build, packaging, dependency, Python-version, and Windows permission behavior.
- User-visible UI controls, hover text, settings, presets, export/import, and
  logs.
- Validation commands, hardware protocols, and first-run instructions.

## Where to Update

- User workflow or safety behavior: `README.md`, `docs/HARDWARE_VALIDATION_PROTOCOL.md`,
  `docs/HARDWARE_DRY_RUN_GUIDE.md`, or `packaging/README_FIRST_PORTABLE.txt`.
- Packaging or build behavior: `docs/WINDOWS_PORTABLE_BUILD.md`,
  `docs/WINDOWS_PYTHON314_BUILD.md`, and `docs/RELEASE_CHECKLIST.md`.
- Release readiness: `docs/RELEASE_CHECKLIST.md`.
- Public attribution or project scope: `NOTICE.md`, `README.md`, or
  `docs/README.md`.

## Commit Hygiene

Before committing:

```powershell
python tests\test_legacy_ui_layout_contracts.py
python -m compileall -q src tests
```

For a release candidate, also run the full validation path documented in
`docs/RELEASE_CHECKLIST.md`.

## Scoped Map Reconstruction Validation

For Map Reconstruction-only UI, visualization, or analysis-control changes:

1. Run focused Map Reconstruction and offscreen Qt regressions.
2. Run Ruff, Black, mypy, and compileall only for changed Map Reconstruction
   sources.
3. Measure `map_reconstruction` coverage separately.

Do not run the full HappyMeasure hardware/acquisition validation suite unless
shared modules, packaging/dependency files, or release metadata change, or the
work is preparing a repository release. Record the two validation scopes
separately in `docs/TESTED_CURRENT.md`.
