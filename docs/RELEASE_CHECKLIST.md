# Release Checklist — HappyMeasure

Use this checklist from a clean release candidate after feature freeze. The public release identity for this cycle is frozen at **1.2b** until publication completes.

## 1. Identity and tree hygiene

Before tagging:

```powershell
git status --short
git log --oneline -8
```

Confirm:

- `src/keith_ivt/version.py`, `pyproject.toml`, and `tools/release/RELEASE_FREEZE_MARKER` all resolve to `1.2b`;
- while the freeze marker exists, screenshot/documentation/packaging/release-only commits preserve `1.2b` instead of incrementing the beta serial;
- no generated/runtime folders, local helper scripts, logs, hardware-smoke artifacts, `build/` or `dist/` are committed;
- no workstation-specific absolute home paths, usernames or physical instrument serial numbers are present in tracked text;
- `docs/RELEASE_NOTES_NEXT.md` describes the 1.2b release scope accurately.

## 2. Automated core validation

Install developer dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run:

```powershell
python tools\release\check_version_sequence.py --base HEAD^ --head HEAD
python -m compileall -q src tests tools\release
python -m black --check src tests tools\release
python -m ruff check src tests tools\release
python -m mypy src/keith_ivt src/happymeasure
python -m pytest -q tests/common tests/happymeasure
python -m pytest tests/common tests/happymeasure --cov=keith_ivt --cov-report=term -q
```

Coverage gate remains `>=95%` for the configured core scope.

## 3. Map Reconstruction release gate

```powershell
python -m pip install -e ".[dev,map]"
$env:QT_QPA_PLATFORM="offscreen"
python -c "import PySide6, pyqtgraph"
python -m mypy src/map_reconstruction
python -m pytest -q tests/map_reconstruction
```

CI owns a dedicated Windows/Python 3.12 job with real Qt dependencies. Dependency-driven skips do not count as a release-gate pass.

For the complete local source-validation environment:

```powershell
python tests\run_full_validation.py
```

## 4. Desktop simulator/UX and screenshots

Automated HappyMeasure UI regressions own state-flow, settings/diagnostics rebuild, live Time-history switching, trace/export behavior and simulator paths. Map UI regressions own the three-stage workflow and project/source replacement behavior.

Before public release, refresh the README screenshots under `docs/screenshots/` from the frozen 1.2b source GUI and visually inspect them. The README owns these six release screenshots:

- `happymeasure-hardware.png`
- `happymeasure-sweep-result.png`
- `happymeasure-front-panel-popup.png`
- `map-reconstruction-preparation.png`
- `map-reconstruction-reconstruction.png`
- `map-reconstruction-analysis.png`

A screenshot refresh is documentation maintenance, not hardware validation. Do not include usernames, private paths, physical serial numbers or unrelated desktop content in captures.

## 5. Hardware evidence

The current release line already has MODEL 2401 no-DUT communication/control evidence recorded in `VALIDATION_STATUS.md`. Do not require another bench session unless later source changes touch serial I/O, source-output safety, acquisition sequencing or hardware cleanup.

If such behavior changes, rerun only the relevant portion of `HARDWARE_VALIDATION_PROTOCOL.md` before release.

Do not upgrade the claim beyond the recorded evidence: no passive-load quantitative accuracy or arbitrary DUT validation was performed in the current release-prep session.

## 6. Windows portable package CI

The `Windows portable package smoke (Python 3.12)` job runs on every push to `main` after the source/Map gates pass. It must be green on the exact commit selected for release. The job:

1. builds HappyMeasure and Map Reconstruction from that commit;
2. audits package structure, forbidden local/runtime content and private identifiers;
3. enforces the Map Reconstruction package-size ceiling;
4. smoke-launches both frozen executables without relying on the source entry points;
5. generates `release-artifacts.json` with artifact sizes and SHA-256 values; and
6. uploads both versioned ZIPs plus the manifest as a short-lived CI artifact.

The local equivalent remains:

```powershell
.\tools\build\Build_Portable_Windows_App.ps1
.\tools\build\Build_Portable_Map_Reconstruction.ps1
python tools\release\audit_portable_artifacts.py --dist dist --manifest dist\release-artifacts.json
```

Never publish an older locally cached ZIP when a newer commit has been selected. Use artifacts built from the exact final commit.

## 7. Release publication

The public identity is already selected: **1.2b**. After all automated gates are green and screenshots are current, tag and publish that exact commit with runtime/package/artifact/tag identity kept consistent. Never reuse an already published version for different source.

Do not change the version again during this release-finalization window. Remove the release-freeze marker only after 1.2b has been published and normal development resumes.

## 8. Post-release

- download each uploaded artifact to a fresh folder and launch it;
- verify hashes and version identity;
- test update detection from the previous public release;
- verify offline update-check failure is non-blocking;
- keep final release evidence in the GitHub Release/changelog, not a workstation-specific path in source documentation.
