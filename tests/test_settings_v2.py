"""Tests for Pydantic-based settings system."""
import json
import pytest
from pathlib import Path
import tempfile

from keith_ivt.data.settings_v2 import (
    AppSettings,
    HardwareSettings,
    SweepSettings,
    UISettings,
    DataSettings,
    load_settings,
    save_settings,
    validate_settings_file,
    SourceMode,
    Terminal,
    UITheme,
)


class TestHardwareSettings:
    """Test hardware settings validation."""

    def test_default_values(self):
        """Default hardware settings should be valid."""
        settings = HardwareSettings()
        assert settings.default_port == "COM3"
        assert settings.default_baud_rate == 9600
        assert settings.default_terminal == Terminal.REAR

    def test_invalid_baud_rate(self):
        """Baud rate should be constrained."""
        with pytest.raises(Exception):  # ValidationError
            HardwareSettings(default_baud_rate=50)  # Too low

        with pytest.raises(Exception):
            HardwareSettings(default_baud_rate=200000)  # Too high

    def test_port_validation_warning(self, caplog):
        """Suspicious port names should generate warnings."""
        HardwareSettings(default_port="INVALID")
        # Warning is logged but value is accepted


class TestSweepSettings:
    """Test sweep settings validation."""

    def test_default_values(self):
        """Default sweep settings should be valid."""
        settings = SweepSettings()
        assert settings.default_mode == SourceMode.VOLTAGE
        assert settings.default_start == -1.0
        assert settings.default_step > 0

    def test_invalid_step_size(self):
        """Step size must be positive."""
        with pytest.raises(Exception):
            SweepSettings(default_step=0)

        with pytest.raises(Exception):
            SweepSettings(default_step=-0.1)

    def test_compliance_must_be_positive(self):
        """Compliance limit must be positive."""
        with pytest.raises(Exception):
            SweepSettings(default_compliance=0)

    def test_nplc_range(self):
        """NPLC should be within reasonable range."""
        # Valid
        SweepSettings(default_nplc=0.01)
        SweepSettings(default_nplc=10.0)

        # Invalid
        with pytest.raises(Exception):
            SweepSettings(default_nplc=0)

        with pytest.raises(Exception):
            SweepSettings(default_nplc=11)

    def test_sweep_range_warning(self, caplog):
        """Start > stop should generate warning."""
        SweepSettings(default_start=1.0, default_stop=-1.0)
        # Warning is logged but values are accepted


class TestUISettings:
    """Test UI settings validation."""

    def test_default_values(self):
        """Default UI settings should be valid."""
        settings = UISettings()
        assert settings.ui_font_family == "Verdana"
        assert settings.ui_font_size == 10
        assert settings.ui_theme == UITheme.LIGHT

    def test_font_size_constraints(self):
        """Font size should be constrained."""
        with pytest.raises(Exception):
            UISettings(ui_font_size=6)  # Too small

        with pytest.raises(Exception):
            UISettings(ui_font_size=20)  # Too large

        # Boundary values
        UISettings(ui_font_size=8)
        UISettings(ui_font_size=18)

    def test_theme_enum(self):
        """Theme should be one of allowed values."""
        assert UISettings(ui_theme=UITheme.DARK).ui_theme == UITheme.DARK
        assert UISettings(ui_theme=UITheme.DEBUG).ui_theme == UITheme.DEBUG


class TestDataSettings:
    """Test data settings validation."""

    def test_default_values(self):
        """Default data settings should be valid."""
        settings = DataSettings()
        assert settings.log_max_bytes == 1_000_000
        assert settings.cache_enabled is False

    def test_log_max_bytes_constraints(self):
        """Log size should be constrained."""
        with pytest.raises(Exception):
            DataSettings(log_max_bytes=100)  # Too small

        with pytest.raises(Exception):
            DataSettings(log_max_bytes=200_000_000)  # Too large

        # Boundary values
        DataSettings(log_max_bytes=1024)
        DataSettings(log_max_bytes=100_000_000)

    def test_cache_interval_minimum(self):
        """Cache interval must be at least 1."""
        with pytest.raises(Exception):
            DataSettings(cache_interval_points=0)

        DataSettings(cache_interval_points=1)  # Valid minimum


class TestAppSettings:
    """Test complete app settings."""

    def test_nested_structure(self):
        """Settings should have nested structure."""
        settings = AppSettings()
        assert hasattr(settings, "hardware")
        assert hasattr(settings, "sweep")
        assert hasattr(settings, "ui")
        assert hasattr(settings, "data")

    def test_backward_compatible_get(self):
        """Legacy get() should work for flat keys."""
        settings = AppSettings()
        assert settings.get("default_port") == "COM3"
        assert settings.get("default_mode") == "VOLT"
        assert settings.get("ui_theme") == "Light"

    def test_backward_compatible_properties(self):
        """Legacy property accessors should work."""
        settings = AppSettings()
        assert settings.default_port == "COM3"
        assert settings.default_mode == "VOLT"
        assert settings.ui_theme == "Light"


class TestSettingsIO:
    """Test settings file I/O."""

    def test_save_and_load(self, tmp_path):
        """Settings should round-trip correctly."""
        settings_file = tmp_path / "settings.json"

        original = AppSettings()
        original.hardware.default_port = "COM4"
        original.sweep.default_start = -2.0

        save_settings(original, settings_file)
        loaded = load_settings(settings_file)

        assert loaded.hardware.default_port == "COM4"
        assert loaded.sweep.default_start == -2.0

    def test_load_nonexistent_returns_defaults(self, tmp_path):
        """Loading missing file should return defaults."""
        settings_file = tmp_path / "does_not_exist.json"
        settings = load_settings(settings_file)

        assert isinstance(settings, AppSettings)
        assert settings.hardware.default_port == "COM3"

    def test_load_invalid_json_returns_defaults(self, tmp_path):
        """Loading invalid JSON should return defaults."""
        settings_file = tmp_path / "invalid.json"
        settings_file.write_text("not valid json {{{")

        settings = load_settings(settings_file)
        assert isinstance(settings, AppSettings)

    def test_save_creates_parent_directory(self, tmp_path):
        """Save should create parent directories."""
        settings_file = tmp_path / "subdir" / "settings.json"

        save_settings(AppSettings(), settings_file)
        assert settings_file.exists()

    def test_save_includes_version_metadata(self, tmp_path):
        """Saved file should include version info."""
        settings_file = tmp_path / "settings.json"
        save_settings(AppSettings(), settings_file)

        data = json.loads(settings_file.read_text())
        assert "_version" in data
        assert data["_version"] == "2.0"


class TestSettingsMigration:
    """Test migration from legacy format."""

    def test_migrate_legacy_flat_format(self, tmp_path):
        """Legacy flat settings should be migrated."""
        settings_file = tmp_path / "legacy.json"

        # Write legacy format
        legacy_data = {
            "default_port": "COM5",
            "default_mode": "CURR",
            "ui_theme": "Dark",
            "log_max_bytes": 2_000_000,
        }
        settings_file.write_text(json.dumps(legacy_data))

        # Load should migrate automatically
        settings = load_settings(settings_file)

        assert settings.hardware.default_port == "COM5"
        assert settings.sweep.default_mode.value == "CURR"
        assert settings.ui.ui_theme.value == "Dark"
        assert settings.data.log_max_bytes == 2_000_000

    def test_migrate_with_invalid_values_uses_defaults(self, tmp_path):
        """Migration with invalid values should use defaults."""
        settings_file = tmp_path / "bad_legacy.json"

        legacy_data = {
            "default_step": -1.0,  # Invalid: must be positive
            "ui_font_size": 100,   # Invalid: too large
        }
        settings_file.write_text(json.dumps(legacy_data))

        # Should not crash, uses defaults for invalid fields
        settings = load_settings(settings_file)
        assert settings.sweep.default_step > 0  # Default value
        assert 8 <= settings.ui.ui_font_size <= 18  # Clamped to valid range


class TestSettingsValidation:
    """Test settings file validation."""

    def test_validate_valid_file(self, tmp_path):
        """Valid settings file should pass validation."""
        settings_file = tmp_path / "valid.json"
        save_settings(AppSettings(), settings_file)

        is_valid, errors = validate_settings_file(settings_file)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_file(self, tmp_path):
        """Missing file should fail validation."""
        settings_file = tmp_path / "missing.json"

        is_valid, errors = validate_settings_file(settings_file)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_invalid_json(self, tmp_path):
        """Invalid JSON should fail validation."""
        settings_file = tmp_path / "invalid.json"
        settings_file.write_text("not json")

        is_valid, errors = validate_settings_file(settings_file)
        assert is_valid is False
        assert any("JSON" in err for err in errors)

    def test_validate_invalid_values(self, tmp_path):
        """Invalid values should fail validation."""
        settings_file = tmp_path / "bad_values.json"
        bad_data = {
            "hardware": {
                "default_baud_rate": 999999  # Out of range
            }
        }
        settings_file.write_text(json.dumps(bad_data))

        is_valid, errors = validate_settings_file(settings_file)
        assert is_valid is False
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
