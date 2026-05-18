# HappyMeasure 1.1 beta (`1.1b1`)

## Highlights

- Startup update checks can now be enabled or disabled from Settings.
- When a newer GitHub Release is detected, HappyMeasure asks before installing.
- The installer handoff downloads the Windows portable release zip, preserves user data, replaces program files in the original portable folder, and restarts the app.
- Installation is blocked while a sweep is active.

## Build artifact name

```text
HappyMeasure-1.1b1-windows-portable.zip
```

## Validation

Run the targeted updater tests before building:

```text
python -m pytest tests/test_update_check.py tests/test_update_installer.py tests/test_settings_v2.py tests/test_version_consistency.py -q
```
