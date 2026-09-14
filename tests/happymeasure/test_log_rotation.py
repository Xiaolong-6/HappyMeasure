from __future__ import annotations

from pathlib import Path

from keith_ivt.data.logging_utils import AppLog
from keith_ivt.data.settings import AppSettings, load_settings, save_settings


def test_lowering_log_limit_rotates_existing_oversized_file(tmp_path: Path) -> None:
    log_path = tmp_path / "log.txt"
    log = AppLog(path=log_path, max_bytes=5_000)
    log.write("x" * 2_000)
    assert log_path.stat().st_size > 1_024

    log.set_max_bytes(1_024)

    rotated = list(tmp_path.glob("log_*.txt"))
    assert len(rotated) == 1
    assert not log_path.exists() or log_path.stat().st_size <= 1_024
    log.write("new message after rotation")
    assert "new message after rotation" in log_path.read_text(encoding="utf-8")
    assert "x" * 100 in rotated[0].read_text(encoding="utf-8")


def test_write_rotates_before_crossing_configured_limit(tmp_path: Path) -> None:
    log_path = tmp_path / "log.txt"
    log = AppLog(path=log_path, max_bytes=10_000)
    log.write("first" * 900)
    assert log_path.exists()
    assert log_path.stat().st_size <= 10_000

    log.write("second" * 1_200)

    assert list(tmp_path.glob("log_*.txt"))
    assert "second" in log_path.read_text(encoding="utf-8")


def test_record_log_disabled_keeps_ui_line_without_persisting(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    save_settings(AppSettings(record_log=False), settings_path)
    load_settings(settings_path)
    log_path = tmp_path / "disabled" / "log.txt"
    try:
        line = AppLog(path=log_path).write("visible in UI only")
        assert "visible in UI only" in line
        assert not log_path.exists()
    finally:
        # Restore the process-global runtime preference for later tests.
        load_settings(tmp_path / "missing-default-settings.json")
