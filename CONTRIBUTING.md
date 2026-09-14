# Contributing

HappyMeasure is hardware-facing software. A change is not complete until operator-facing documentation and the relevant validation gate have been considered.

## Documentation rule

Every change must either update the owner documentation or explicitly state why no documentation change is needed. Use `docs/README.md` to locate the owner.

Do not create date-by-date handoff/test diary documents. Remove superseded instructions after preserving still-current contracts in their owner document.

## Internal version rule

Every commit must increment the internal beta serial by exactly one and keep these two files consistent:

- `src/keith_ivt/version.py`
- `pyproject.toml`

Example: `1.1b7` → `1.1b8` on the very next commit, even when the commit only changes docs/tests. CI checks commit-by-commit history, not just final HEAD. See `docs/VERSIONING.md`.

The public release version/tag is a separate human decision made after release validation.

## Privacy/repository hygiene

Do not commit:

- `C:\Users\<real-user>\...`, `/home/<real-user>/...`, `/Users/<real-user>/...` or equivalent workstation-specific paths;
- physical instrument serial numbers;
- personal local directory layouts, logs, caches or hardware-smoke result folders;
- generated `build/` / `dist/` content.

Use relative paths, environment variables and synthetic hardware identifiers in tests/examples.

## Commit hygiene

Before committing at minimum:

```powershell
python tools\release\check_version_sequence.py --base HEAD^ --head HEAD
python -m compileall -q src tests tools\release
python -m black --check src tests tools\release
python -m ruff check src tests tools\release
```

Run focused regressions for changed behavior. Shared hardware, state, settings, packaging or release changes require the broader validation in `docs/RELEASE_CHECKLIST.md`.

## Map Reconstruction

For Map-only changes install optional GUI dependencies and run the owned offscreen Qt domain:

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

Automated/simulator tests are not real-hardware certification. Existing release-line hardware evidence is recorded in `docs/VALIDATION_STATUS.md`; rerun physical tests only when the changed boundary invalidates that evidence or the release owner explicitly asks for deeper bench validation.
