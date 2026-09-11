from __future__ import annotations

import ast
import inspect
import textwrap
from dataclasses import fields
from pathlib import Path

from keith_ivt.data.settings import AppSettings
from keith_ivt.diagnostics.hardware_self_test import _supported_identity
from keith_ivt.ui.settings_preset_actions import SettingsPresetMixin
from keith_ivt.ui.settings_roundtrip import CURRENT_SETTINGS_OVERLAY_FIELDS, SettingsRoundTripMixin

ROOT = Path(__file__).resolve().parents[2]


class _Var:
    def __init__(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value


class _BaseSettingsSnapshot:
    def _current_settings(self) -> AppSettings:
        return AppSettings(check_updates_on_startup=True)


class _SettingsHarness(SettingsRoundTripMixin, _BaseSettingsSnapshot):
    def __init__(self, check_updates: bool) -> None:
        self.check_updates_on_startup = _Var(check_updates)


def _legacy_snapshot_fields() -> set[str]:
    source = textwrap.dedent(inspect.getsource(SettingsPresetMixin._current_settings))
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "AppSettings":
            return {kw.arg for kw in node.keywords if kw.arg is not None}
    raise AssertionError("SettingsPresetMixin._current_settings must construct AppSettings")


def test_update_check_preference_survives_current_settings_snapshot() -> None:
    assert _SettingsHarness(False)._current_settings().check_updates_on_startup is False
    assert _SettingsHarness(True)._current_settings().check_updates_on_startup is True


def test_current_settings_snapshot_has_explicit_appsettings_field_parity() -> None:
    expected = {field.name for field in fields(AppSettings)}
    represented = _legacy_snapshot_fields() | set(CURRENT_SETTINGS_OVERLAY_FIELDS)
    assert represented == expected


def test_hardware_diagnostic_model_check_uses_actual_idn_model_field() -> None:
    assert _supported_identity("KEITHLEY INSTRUMENTS INC.,MODEL 2400,12345,A01")
    assert _supported_identity("KEITHLEY INSTRUMENTS INC.,MODEL 2401,12345,B02")
    assert _supported_identity("KEITHLEY INSTRUMENTS INC.,MODEL 2410,12345,C01")
    assert not _supported_identity("OTHER,MODEL 2401,12345,B02")
    assert not _supported_identity("KEITHLEY INSTRUMENTS INC.,MODEL 2450,SERIAL2401,1.0")
    assert not _supported_identity("KEITHLEY INSTRUMENTS INC.,MODEL 9999,SERIAL2400,1.0")
    assert not _supported_identity("KEITHLEY 2401")


def test_ci_has_non_skipping_map_qt_release_gate() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert 'pip install -e ".[dev,map]"' in ci
    assert "QT_QPA_PLATFORM: offscreen" in ci
    assert "import PySide6, pyqtgraph" in ci
    assert 'pytest -q -k "map_reconstruction or phase_window"' in ci
