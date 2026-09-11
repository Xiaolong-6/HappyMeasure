from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib import error

import pytest

from keith_ivt.data.backup import autosave_result, default_backup_dir, safe_filename
from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, SweepResult
from keith_ivt.services import update_check
from keith_ivt.services.update_check import (
    check_github_release,
    select_portable_zip_asset_details,
)
from keith_ivt.utils.thread_safe import ThreadSafeBuffer, ThreadSafeXYBuffer


class _DummyResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _install_payload(monkeypatch, payload: object) -> None:
    monkeypatch.setattr(
        update_check.request,
        "urlopen",
        lambda _req, timeout: _DummyResponse(payload),
    )


def _small_result(device_name: str = "Device A") -> SweepResult:
    config = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=0.01,
        nplc=0.1,
        device_name=device_name,
    )
    return SweepResult(config, [SweepPoint(0.0, 1e-9)])


def test_backup_helpers_create_safe_timestamped_csv(tmp_path: Path) -> None:
    assert safe_filename("  ..Ge sample / 01..  ") == "Ge_sample_01"
    assert safe_filename("***", fallback="fallback") == "fallback"
    assert default_backup_dir(tmp_path) == tmp_path / "backups" / "auto"

    path = autosave_result(
        _small_result("Ge sample / 01"), tmp_path / "custom-backups"
    )

    assert path.exists()
    assert path.parent == tmp_path / "custom-backups"
    assert path.name.endswith("_Ge_sample_01_VOLT_backup.csv")
    text = path.read_text(encoding="utf-8")
    assert "single-v2" in text
    assert "Ge sample / 01" in text


def test_thread_safe_buffer_overflow_clear_and_empty_paths() -> None:
    with pytest.raises(ValueError):
        ThreadSafeBuffer[int](maxsize=0)

    buffer = ThreadSafeBuffer[int](maxsize=2)
    assert buffer.is_empty()
    assert buffer.pop_front() is None

    buffer.append(1)
    buffer.append(2)
    buffer.append(3)
    assert buffer.get_snapshot() == [2, 3]
    assert buffer.had_overflow() is True
    assert buffer.had_overflow() is False

    buffer.clear()
    assert buffer.is_empty()
    assert buffer.had_overflow() is False


def test_thread_safe_xy_buffer_is_bounded_thread_safe_and_clearable() -> None:
    with pytest.raises(ValueError):
        ThreadSafeXYBuffer(maxsize=0)

    buffer = ThreadSafeXYBuffer(maxsize=200)

    def worker(offset: int) -> None:
        for index in range(100):
            value = float(offset + index)
            buffer.append(value, -value)

    threads = [
        threading.Thread(target=worker, args=(offset,)) for offset in (0, 1000, 2000)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    x_values, y_values = buffer.get_snapshot()
    assert len(buffer) == len(x_values) == len(y_values) == 200
    assert all(
        x_value == -y_value for x_value, y_value in zip(x_values, y_values)
    )

    buffer.clear()
    assert buffer.get_snapshot() == ([], [])


def test_update_check_handles_http_and_unexpected_failures(monkeypatch) -> None:
    def raise_http(_req, timeout):
        raise error.HTTPError(
            "https://example.invalid", 503, "unavailable", None, None
        )

    monkeypatch.setattr(update_check.request, "urlopen", raise_http)
    result = check_github_release("Xiaolong-6", "HappyMeasure", "1.1b6")
    assert result["status"] == "error"
    assert "503" in str(result["message"])

    def raise_unexpected(_req, timeout):
        raise RuntimeError("broken decoder")

    monkeypatch.setattr(update_check.request, "urlopen", raise_unexpected)
    result = check_github_release("Xiaolong-6", "HappyMeasure", "1.1b6")
    assert result["status"] == "error"
    assert "broken decoder" in str(result["message"])


def test_update_check_handles_empty_missing_invalid_and_ahead_release_metadata(
    monkeypatch,
) -> None:
    _install_payload(monkeypatch, [])
    result = check_github_release("Xiaolong-6", "HappyMeasure", "1.1b6")
    assert result["status"] == "current"
    assert result["message"] == "No published releases found."

    _install_payload(monkeypatch, [{"draft": False, "tag_name": ""}])
    assert check_github_release("X", "Y", "1.1b6")["status"] == "error"

    _install_payload(monkeypatch, [{"draft": False, "tag_name": "not-a-version"}])
    result = check_github_release("X", "Y", "1.1b6")
    assert result["status"] == "error"
    assert "Unsupported version format" in str(result["message"])

    _install_payload(
        monkeypatch,
        [
            {
                "draft": False,
                "tag_name": "v1.1b5",
                "html_url": "https://example.invalid/v1.1b5",
            }
        ],
    )
    result = check_github_release("X", "Y", "1.1b6")
    assert result["status"] == "ahead"
    assert result["latest_version"] == "v1.1b5"


def test_portable_asset_selection_rejects_invalid_assets_and_prefers_best_match() -> None:
    assert select_portable_zip_asset_details({}) == (None, None, None)
    assert select_portable_zip_asset_details({"assets": "not-a-list"}) == (
        None,
        None,
        None,
    )
    assert select_portable_zip_asset_details(
        {"assets": [{"name": "notes.txt", "browser_download_url": "x"}]}
    ) == (None, None, None)

    weak = {
        "name": "HappyMeasure-win.zip",
        "browser_download_url": "weak",
        "digest": "sha256:not-valid",
    }
    strong = {
        "name": "HappyMeasure-1.1b6-windows-portable.zip",
        "browser_download_url": "strong",
        "digest": "sha256:" + "A" * 64,
    }
    name, url, digest = select_portable_zip_asset_details(
        {
            "assets": [
                "bad",
                {"name": "Source code (zip)", "browser_download_url": "source"},
                weak,
                strong,
            ]
        }
    )
    assert name == strong["name"]
    assert url == "strong"
    assert digest == "a" * 64
