# Release Checklist — HappyMeasure 1.1b6

Use this checklist from a clean release branch after feature freeze. `v1.1b5` already exists publicly; this source line must use `1.1b6` / `v1.1b6`.

## 1. Identity and tree hygiene

Expected identity:

- prose: `1.1 beta 6`
- package: `1.1b6`
- tag: `v1.1b6`
- artifacts (same release, two independent portable ZIPs sharing one version):
  - `HappyMeasure-1.1b6-windows-portable.zip` (acquisition application)
  - `MapReconstruction-1.1b6-windows-portable.zip` (standalone companion post-processing application; no separate version history)

Before tagging:

```powershell
git status --short
git log --oneline -5
```

No generated/runtime folders, local helper scripts, logs, hardware-smoke artifacts, `build/` or `dist/` may be committed.

Check version consistency in:

- `src/keith_ivt/version.py`
- `pyproject.toml`
- `README.md`
- `docs/CHANGELOG.md`
- `docs/RELEASE_NOTES_v1.1b6.md`

## 2. Automated core validation

Install the core developer dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run:

```powershell
python -m compileall -q src tests
python -m black --check src tests
python -m ruff check src tests
python -m mypy src/keith_ivt src/happymeasure
python -m pytest -q tests/common tests/happymeasure
python -m pytest tests/common tests/happymeasure --cov=keith_ivt --cov-report=term -q
```

Coverage gate remains `>=95%` for the configured core scope. Do not lower it to close a release.

## 3. Map Reconstruction release gate

This is mandatory for `1.1b6` because Map Reconstruction has substantial release-visible changes. Map dependencies remain optional for the normal HappyMeasure install, so the Qt suite is intentionally owned by its own gate rather than the core Python matrix.

```powershell
python -m pip install -e ".[dev,map]"
$env:QT_QPA_PLATFORM="offscreen"
python -c "import PySide6, pyqtgraph"
python -m mypy src/map_reconstruction
python -m pytest -q tests/map_reconstruction
```

CI has a dedicated Windows/Python 3.12 job that installs `.[dev,map]`. A missing dependency must fail the job rather than silently skipping the Qt suite.

For the complete local release validation after both dependency sets are installed, also run:

```powershell
python tests\run_full_validation.py
```

## 4. Desktop simulator/UX smoke

Follow `MANUAL_SMOKE_TESTS.md` plus the current list in `VALIDATION_STATUS.md`.

Pay particular attention to:

- repeated Start/Pause/Resume/Stop/restart;
- short window / Windows scaling and scrollability;
- Advanced Acquisition Standard/Fast/Custom state;
- long Time plot smoothness and full completed trace;
- trace import/export/rename/delete;
- Settings review preserving disabled update checks;
- UI Diagnostics return path;
- Map CSV replacement, project round-trip and maximized startup.

## 5. Hardware safety gate

Follow `HARDWARE_VALIDATION_PROTOCOL.md` in order. Never skip directly to a real DUT.

Record:

- model/firmware from `*IDN?`;
- port/baud/terminal/wiring;
- compliance/range/profile;
- output-off confirmation after normal completion, Stop, Abort/error and disconnect;
- generated CSV/log artifacts.

Hardware Diagnostics is communication/output-off only and must never enable output or issue a measurement read.

## 6. Windows portable packages

Build only after source gates pass. Build scripts use dedicated
`.venv-build*` environments and never touch the developer `.venv`.

HappyMeasure acquisition application:

```powershell
.\tools\build\Build_Portable_Windows_App.ps1
```

or:

```bat
tools\build\Build_Portable_Windows_App.bat
```

Verify:

- `dist\HappyMeasure\HappyMeasure.exe`
- `dist\HappyMeasure\_internal`
- required readme/safety/config files
- versioned portable ZIP
- packaged app launches and closes cleanly
- simulator connect + short sweep works
- About/update-check UI has no import error

Map Reconstruction standalone companion (no Python, no HappyMeasure, no SMU needed):

```powershell
.\tools\build\Build_Portable_Map_Reconstruction.ps1
```

or:

```bat
tools\build\Build_Portable_Map_Reconstruction.bat
```

Verify:

- `dist\MapReconstruction\MapReconstruction.exe`
- `dist\MapReconstruction\_internal`
- `README_FIRST.txt` describing standalone use
- versioned portable ZIP
- packaged app launches and closes cleanly without system Python
- a minimal HappyMeasure CSV imports and a `.hmmap` save/open smoke passes

Record SHA-256 and package size of both ZIPs in the final release notes.

## 7. Tag and GitHub Release

Only after source + desktop + selected hardware gate passes:

```powershell
git tag v1.1b6
git push origin main --tags
```

Create a prerelease named `HappyMeasure 1.1b6`, upload both verified portable ZIPs, and include the actual validation level. Do not reuse or replace the published `v1.1b5` asset/tag.

## 8. Post-release

- download the uploaded ZIP to a fresh folder and launch it;
- verify GitHub exposes the expected SHA-256 digest metadata;
- test update detection from the previous release;
- verify offline update-check failure is non-blocking;
- update `VALIDATION_STATUS.md` / `CHANGELOG.md` with the final released state in the next normal source commit if needed.
