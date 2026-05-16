from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib import error

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.services import update_check
from keith_ivt.services.update_check import check_github_release, is_newer_version, parse_version


class DummyResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def install_urlopen(monkeypatch, payload):
    def fake_urlopen(_req, timeout):
        assert timeout == 3.0
        return DummyResponse(payload)

    monkeypatch.setattr(update_check.request, "urlopen", fake_urlopen)


def test_version_comparator_supports_expected_formats() -> None:
    assert parse_version("0.7.0")
    assert parse_version("v0.7.0-alpha.1")
    assert parse_version("0.7.0-beta.1")
    assert parse_version("0.7.0-rc.1")
    assert parse_version("0.7a1")
    assert is_newer_version("v0.7.0-alpha.2", "0.7a1")


def test_prerelease_ordering_alpha_beta_rc_stable() -> None:
    ordered = [
        "0.7.0-alpha.1",
        "0.7.0-beta.1",
        "0.7.0-rc.1",
        "0.7.0",
    ]
    assert sorted(ordered, key=parse_version) == ordered
    assert is_newer_version("0.7.0", "0.7.0-rc.1")
    assert is_newer_version("0.8.0-alpha.1", "0.7.0")


def test_remote_newer_release(monkeypatch) -> None:
    install_urlopen(
        monkeypatch,
        [
            {
                "draft": False,
                "prerelease": True,
                "tag_name": "v0.7.0-alpha.2",
                "html_url": (
                    "https://github.com/Xiaolong-6/HappyMeasure/releases/tag/v0.7.0-alpha.2"
                ),
            }
        ],
    )

    result = check_github_release("Xiaolong-6", "HappyMeasure", "0.7a1")

    assert result["status"] == "newer"
    assert result["latest_version"] == "v0.7.0-alpha.2"
    assert result["message"] == "New version available: v0.7.0-alpha.2. Please upgrade manually."
    assert result["release_url"].endswith("/v0.7.0-alpha.2")


def test_remote_current_release(monkeypatch) -> None:
    install_urlopen(
        monkeypatch,
        [
            {
                "draft": False,
                "prerelease": False,
                "tag_name": "v0.7.0",
                "html_url": "https://github.com/Xiaolong-6/HappyMeasure/releases/tag/v0.7.0",
            }
        ],
    )

    result = check_github_release("Xiaolong-6", "HappyMeasure", "0.7.0")

    assert result["status"] == "current"
    assert result["latest_version"] == "v0.7.0"
    assert result["release_url"].endswith("/v0.7.0")


def test_include_prerelease_false_skips_prereleases(monkeypatch) -> None:
    install_urlopen(
        monkeypatch,
        [
            {
                "draft": False,
                "prerelease": True,
                "tag_name": "v0.8.0-alpha.1",
                "html_url": "alpha",
            },
            {"draft": False, "prerelease": False, "tag_name": "v0.7.0", "html_url": "stable"},
        ],
    )

    result = check_github_release(
        "Xiaolong-6",
        "HappyMeasure",
        "0.7.0",
        include_prerelease=False,
    )

    assert result["status"] == "current"
    assert result["release_url"] == "stable"


def test_offline_return(monkeypatch) -> None:
    def fake_urlopen(_req, timeout):
        raise error.URLError("offline")

    monkeypatch.setattr(update_check.request, "urlopen", fake_urlopen)

    result = check_github_release("Xiaolong-6", "HappyMeasure", "0.7a1")

    assert result["status"] == "offline"
    assert result["message"] == "Update check unavailable: offline."


def test_error_return_for_bad_payload(monkeypatch) -> None:
    install_urlopen(monkeypatch, {"message": "rate limited"})

    result = check_github_release("Xiaolong-6", "HappyMeasure", "0.7a1")

    assert result["status"] == "error"
    assert "Update check unavailable" in result["message"]


def test_invalid_version_rejected() -> None:
    with pytest.raises(ValueError):
        parse_version("latest")


def test_ui_update_check_cache_contract() -> None:
    ui_source = (SRC / "keith_ivt" / "ui" / "simple_app.py").read_text(encoding="utf-8")
    panel_source = (SRC / "keith_ivt" / "ui" / "panels.py").read_text(encoding="utf-8")

    assert "_update_check_in_progress" in ui_source
    assert "_last_update_check_result" in ui_source
    assert "_last_update_check_timestamp" in ui_source
    assert "UPDATE_CHECK_CACHE_SECONDS = 30 * 60" in ui_source
    assert "_show_cached_update_check_result()" in panel_source
