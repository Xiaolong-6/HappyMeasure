# Windows Portable Build With Python 3.14

This document contains only the Python 3.14-specific packaging path and workaround. The common portable-build contract, output layout, first-run files, safety gate and release artifact rules are owned by `WINDOWS_PORTABLE_BUILD.md`.

## Use the dedicated 3.14 launcher

From Windows, run one of:

```text
tools\build\Build_Portable_Windows_App_Python314.bat
```

```powershell
.\tools\build\Build_Portable_Windows_App_Python314.ps1
```

This path intentionally uses Python 3.14 only; it does not fall back to 3.13/3.12/3.11.

## Why this path is separate

Some Windows/Python 3.14 environments have shown temporary-directory permission failures during virtual-environment/editable-install setup and pytest cleanup. The maintained 3.14 packaging path therefore uses explicit dependencies and `PYTHONPATH=src` rather than treating a full editable-install pytest run as part of packaging.

This does **not** replace the source release gates. Source/CI validation must already be green before building the portable artifact.

## Packaging-time validation

The 3.14 build path performs its maintained import/build smoke checks and produces the same onedir artifact contract described in `WINDOWS_PORTABLE_BUILD.md`.

After packaging, manually verify at least:

1. `dist\HappyMeasure\HappyMeasure.exe` launches and closes cleanly.
2. Debug simulator acquisition works.
3. CSV export and log writing work.
4. STOP returns the UI to a safe state.
5. Map Reconstruction launches if included by the package.
6. Hardware preflight is run before any real DUT is connected.

## Temp-directory workaround

If Python 3.14 fails before the maintained script can create/use its environment because `ensurepip` or pip cannot write/clean a temporary wheel directory, use a repository-local dependency target:

```powershell
$root = (Resolve-Path .).Path
$env:TEMP = Join-Path $root ".tmp-build"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $root ".pip-cache"
python -m pip install --target .build-deps matplotlib pyserial pyinstaller
$env:PYTHONPATH = (Join-Path $root ".build-deps") + ";" + (Join-Path $root "src")
python -c "from PyInstaller.__main__ import run; run(['--noconfirm','--clean','--distpath','dist','--workpath','build','packaging\\HappyMeasure.spec'])"
```

After this manual fallback, copy the same first-run files required by the common build contract. Do not invent a different portable layout for the workaround.

Repository-local `.build-deps`, `.pip-cache`, `.tmp-build`, `build`, and `dist` directories are build/runtime artifacts and must not be committed.

## Interpreter check

If the launcher cannot find Python 3.14, verify:

```bat
py -3.14 --version
python --version
```

At least one configured launcher path must report Python 3.14. For normal 3.12/3.11/3.13 packaging, use `WINDOWS_PORTABLE_BUILD.md` instead.
