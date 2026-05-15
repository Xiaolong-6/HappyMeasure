# Settings System Migration Guide (v1 → v2)

This guide explains the new Pydantic-based settings system in HappyMeasure 0.6.0 and how to migrate from the legacy dataclass format.

## Why Migrate?

The new settings system provides:

1. **Runtime Validation**: Catch configuration errors immediately, not at runtime
2. **Type Safety**: Full IDE support with autocomplete and type hints
3. **Value Constraints**: Automatic range checking for numeric values
4. **Clear Error Messages**: Understandable feedback when settings are invalid
5. **Structured Organization**: Settings grouped by category (hardware, sweep, ui, data)
6. **Automatic Migration**: Legacy files are automatically converted

## Key Differences

| Feature | Legacy (v1) | New (v2) |
|---------|-------------|----------|
| **Format** | Flat dictionary | Nested structure |
| **Validation** | Manual `clamp()` functions | Pydantic validators |
| **Type Safety** | None | Full type hints |
| **Error Handling** | Silent fallback to defaults | Clear error messages |
| **IDE Support** | No autocomplete | Full IntelliSense |
| **Migration** | N/A | Automatic |

## Usage Examples

### Legacy Format (v1)

```python
from keith_ivt.data.settings import AppSettings, load_settings, save_settings

settings = load_settings()
port = settings.default_port  # Flat access
settings.default_port = "COM4"
save_settings(settings)
```

### New Format (v2)

```python
from keith_ivt.data.settings_v2 import AppSettings, load_settings, save_settings

settings = load_settings()
port = settings.hardware.default_port  # Structured access
settings.hardware.default_port = "COM4"
save_settings(settings)
```

### Backward Compatibility

The new system maintains backward compatibility:

```python
settings = load_settings()

# Both work:
port = settings.hardware.default_port  # New way
port = settings.get("default_port")    # Legacy way
port = settings.default_port           # Property accessor
```

## Settings Structure

### Hardware Settings

```python
settings.hardware.default_port          # "COM3"
settings.hardware.default_baud_rate     # 9600
settings.hardware.default_terminal      # Terminal.REAR
settings.hardware.default_sense_mode    # SenseMode.TWO_WIRE
settings.hardware.default_debug_model   # "Linear resistor 10 kΩ"
```

### Sweep Settings

```python
settings.sweep.default_mode             # SourceMode.VOLTAGE
settings.sweep.default_start            # -1.0
settings.sweep.default_stop             # 1.0
settings.sweep.default_step             # 0.1
settings.sweep.default_compliance       # 0.01
settings.sweep.default_nplc             # 1.0
settings.sweep.default_autorange        # True
# ... and more
```

### UI Settings

```python
settings.ui.ui_font_family              # "Verdana"
settings.ui.ui_font_size                # 10
settings.ui.ui_theme                    # UITheme.LIGHT
settings.ui.default_plot_layout         # PlotLayout.AUTO
```

### Data Settings

```python
settings.data.log_max_bytes             # 1_000_000
settings.data.cache_enabled             # False
settings.data.cache_interval_points     # 10
settings.data.default_device_name       # "Device_1"
```

## Validation Examples

### Automatic Range Checking

```python
from keith_ivt.data.settings_v2 import UISettings

# This will raise ValidationError
try:
    settings = UISettings(ui_font_size=50)  # Max is 18
except ValidationError as e:
    print(e)  # Clear error message
```

### Enum Constraints

```python
from keith_ivt.data.settings_v2 import UITheme, UISettings

# Valid
settings = UISettings(ui_theme=UITheme.DARK)

# Invalid - will raise ValidationError
settings = UISettings(ui_theme="InvalidTheme")
```

## Migration Steps

### For End Users

No action needed! The migration happens automatically:

1. First launch after upgrade detects legacy `settings.json`
2. Automatically converts to new nested format
3. Saves migrated file with version metadata
4. Application continues normally

### For Developers

Update imports:

```python
# Old
from keith_ivt.data.settings import AppSettings

# New
from keith_ivt.data.settings_v2 import AppSettings
```

Update access patterns (recommended but not required):

```python
# Old
settings.default_port = "COM4"

# New (preferred)
settings.hardware.default_port = "COM4"
```

## File Format Comparison

### Legacy Format (v1)

```json
{
  "default_port": "COM3",
  "default_mode": "VOLT",
  "ui_theme": "Light",
  "log_max_bytes": 1000000
}
```

### New Format (v2)

```json
{
  "_version": "2.0",
  "_comment": "HappyMeasure settings - do not edit manually",
  "hardware": {
    "default_port": "COM3",
    "default_baud_rate": 9600
  },
  "sweep": {
    "default_mode": "VOLT",
    "default_start": -1.0
  },
  "ui": {
    "ui_font_family": "Verdana",
    "ui_theme": "Light"
  },
  "data": {
    "log_max_bytes": 1000000
  }
}
```

## Validating Settings Files

Use the validation utility:

```python
from keith_ivt.data.settings_v2 import validate_settings_file

is_valid, errors = validate_settings_file("config/settings.json")
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

## Troubleshooting

### Settings File Not Loading

Check for validation errors:

```python
is_valid, errors = validate_settings_file()
print(errors)
```

Common issues:
- Invalid JSON syntax
- Out-of-range values (e.g., font size > 18)
- Invalid enum values (e.g., theme = "Blue")

### Reverting to Defaults

Delete or rename the settings file:

```bash
mv config/settings.json config/settings.json.backup
# Application will create new defaults on next launch
```

### Manual Editing

If you must edit the JSON file manually:

1. Use a JSON validator first
2. Check value ranges in the code
3. Run `validate_settings_file()` after editing
4. Backup before making changes

## API Reference

### Classes

- `AppSettings` - Root settings container
- `HardwareSettings` - Hardware connection settings
- `SweepSettings` - Measurement sweep defaults
- `UISettings` - User interface appearance
- `DataSettings` - Data management options

### Enums

- `SourceMode` - VOLTAGE, CURRENT
- `Terminal` - FRONT, REAR
- `SenseMode` - TWO_WIRE, FOUR_WIRE
- `SweepKind` - STEP, TIME, ADAPTIVE
- `UITheme` - LIGHT, DARK, DEBUG
- `PlotLayout` - AUTO, SINGLE, HORIZONTAL, VERTICAL, GRID

### Functions

- `load_settings(path)` - Load with validation and migration
- `save_settings(settings, path)` - Save with version metadata
- `validate_settings_file(path)` - Validate without loading

## Timeline

- **0.5.x**: Legacy format only
- **0.6.0-alpha**: Both formats supported, auto-migration
- **0.6.0-beta**: Legacy format deprecated (warnings issued)
- **0.7.0**: Legacy format removed

## Need Help?

- See `src/keith_ivt/data/settings_v2.py` for implementation details
- Check `tests/test_settings_v2.py` for usage examples
- Review validation constraints in the Pydantic model definitions
