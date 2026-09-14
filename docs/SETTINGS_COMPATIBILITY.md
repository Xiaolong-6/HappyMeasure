# Settings compatibility contract

HappyMeasure persists desktop settings through the flat `keith_ivt.data.settings.AppSettings` dataclass in `config/settings.json`.

The format is intentionally backward-compatible: missing/invalid values fall back locally, known aliases are normalized, and unknown keys are ignored rather than crashing startup.

## Persisted application preferences

Application-level preferences include:

- `auto_save_backup` — automatically save completed/partial recovered measurements; default `true`;
- `record_log` — persist normal application event logging; default `true`;
- `log_max_bytes` — rotating event-log size limit;
- `cache_enabled` / `cache_interval_points`;
- hardware connection defaults;
- Time-plot display preferences;
- UI appearance and startup behavior;
- update-check preference.

Manual **Backup now** remains available even when automatic backup is disabled.

## Time-plot settings

Time-plot history is display policy only:

- `time_plot_history_mode`: `All data` or `Last N points`;
- `time_plot_history_points`: positive integer;
- `time_plot_marker_mode`: `Auto`, `On`, `Off`;
- `time_plot_refresh_ms`: `100`, `250`, `500`, `1000`.

The live History control can be changed while a measurement is running. It must not truncate `_live_points`, completed `SweepResult.points`, CSV export or project data.

## Settings review dialog

`Review Default Settings...` must be able to open even when a setting has no dedicated live Tk variable. Application-only fields fall back to the current `AppSettings` value rather than assuming a widget/variable exists.

The review/save path must preserve all persisted fields, including values that differ from defaults.

## Compatibility rules

Adding a persisted field requires:

1. a default in `AppSettings`;
2. sanitizer/coercion support when needed;
3. Settings review round-trip support if user-editable;
4. a regression showing old JSON without the field still loads;
5. a round-trip regression when silent reset would be user-visible.

Do not reintroduce the removed experimental `settings_v2.py`/alternate persistence model unless it deliberately becomes the single runtime owner with an explicit migration/rollback design.

## Resetting settings

For troubleshooting, close HappyMeasure and rename/remove `config/settings.json`; missing values will fall back to built-in defaults. Keep a copy when user-specific connection or plotting preferences matter.
