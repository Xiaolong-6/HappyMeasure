# Contributing

HappyMeasure is hardware-facing software. A code change is not complete until operator-facing documentation and the relevant validation gate have been considered.

## Documentation rule

Every change must either update the owner documentation or explicitly state why no documentation change is needed.

Use `docs/README.md` to locate the owner. In particular:

- user/safety behavior → `README.md` and hardware/user owner docs;
- packaging/build → `docs/WINDOWS_PORTABLE_BUILD.md` / `docs/RELEASE_CHECKLIST.md`;
- current validation status → `docs/VALIDATION_STATUS.md`;
- release history → `docs/CHANGELOG.md` / versioned release notes;
- architecture/state contracts → `docs/ARCHITECTURE_CURRENT.md`, `docs/STATE_MACHINE.md`, `docs/ERROR_RECOVERY.md`.

Do not create date-by-date handoff/test diary documents.

## Commit hygiene

Before committing at minimum:

```powershell
python -m compileall -q src tests
python -m black --check src tests
python -m ruff check src tests
```

Run focused regressions for the changed behavior. Shared hardware, state, settings, packaging or release changes require the broader validation in `docs/RELEASE_CHECKLIST.md`.

## Map Reconstruction

For Map-only changes install the optional GUI dependencies and run the owned offscreen Qt test domain:

```powershell
python -m pip install -e ".[dev,map]"
$env:QT_QPA_PLATFORM="offscreen"
python -c "import PySide6, pyqtgraph"
python -m mypy src/map_reconstruction
python -m pytest -q tests/map_reconstruction
```

A release candidate must run this gate with real Qt dependencies; a dependency-driven skip is not a release-gate pass.

## Regression-test discipline

- Prefer behavioral contracts over implementation-string assertions.
- Preserve tests for output-off, recovery, settings/file compatibility and scientific-data integrity.
- Remove/consolidate obsolete tests only when stronger coverage remains and the rationale is clear.
- Never lower the coverage threshold to close a release.

## Hardware

Automated/simulator tests are not real-hardware certification. Follow `docs/HARDWARE_VALIDATION_PROTOCOL.md` for staged hardware work, starting from no-DUT/preflight checks.
