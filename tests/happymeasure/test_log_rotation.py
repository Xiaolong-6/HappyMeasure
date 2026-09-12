from __future__ import annotations

from pathlib import Path

from keith_ivt.data.logging_utils import AppLog


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
