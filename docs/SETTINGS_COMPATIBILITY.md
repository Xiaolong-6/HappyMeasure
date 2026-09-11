# Settings compatibility contract

This document describes the settings format used by the HappyMeasure desktop application in the `1.1b6` release line.

## Runtime owner

The active desktop settings implementation is `src/keith_ivt/data/settings.py`.

`AppSettings` is a flat dataclass persisted as `config/settings.json`. The format is intentionally simple and backward-compatible: missing or invalid values fall back to safe defaults, known legacy spellings are normalized, and unknown keys are ignored rather than crashing application startup.

The Pydantic module `src/keith_ivt/data/settings_v2.py` exists as an experimental/alternate model and has its own tests, but it is **not** the persistence owner for the desktop application in `1.1b6`. Do not tell users to convert their settings JSON to the nested v2 example unless the runtime is deliberately migrated in a future release.

## Load/save behavior

`load_settings()`:

- returns defaults when the file is absent, unreadable, malformed JSON, or not an object;
- accepts only keys present in the current `AppSettings` dataclass;
- coerces supported boolean/string/numeric legacy values where safe;
- clamps bounded values such as UI font size and log size;
- normalizes known aliases such as `FRONT` → `FRON` and historical theme names;
- preserves valid user choices such as `check_updates_on_startup=False`.

`save_settings()` writes the sanitized flat dictionary back to JSON. Adding a new persisted field therefore requires all of the following:

1. add a default to `AppSettings`;
2. add coercion/validation in `sanitize_settings_dict()` if the field is not a free-form string;
3. include the field in the Settings UI round-trip if it is user-editable there;
4. add a regression proving an older JSON file without the field still loads;
5. add a round-trip regression when silent reset would be user-visible.

## Current plot settings

Time-plot display preferences are application/view settings and do not change acquired data:

- `time_plot_marker_mode`: `Auto`, `On`, or `Off`;
- `time_plot_history_mode`: `All data` or `Last N points`;
- `time_plot_history_points`: positive integer;
- `time_plot_refresh_ms`: one of `100`, `250`, `500`, or `1000`.

`Last N points` applies to the live display path only. The authoritative live buffer, completed `SweepResult`, CSV export, and project data remain complete.

## Compatibility rules

- Existing flat settings files must remain readable across beta updates.
- Missing fields use current defaults; a new field must never make an old file invalid.
- Invalid individual values should fall back locally rather than discarding unrelated valid settings.
- The Settings review/save path must preserve all persisted user preferences, including values that differ from defaults.
- Do not introduce a second automatic migration format without first making it the single runtime owner and documenting rollback/compatibility behavior.

## Resetting settings

For troubleshooting, close HappyMeasure and rename or remove `config/settings.json`; the application will recreate defaults on the next save/startup path. Keep a copy if user-specific ports, plotting preferences, or update-check settings matter.
