from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.services.update_installer import (
    PRESERVED_NAMES,
    UpdateLaunchPlan,
    build_powershell_updater_script,
    default_install_dir,
    is_frozen_app,
    launch_update_installer,
    write_powershell_updater_script,
)

ASSET_URL = "https://github.com/Xiaolong-6/HappyMeasure/releases/download/v1.1b3/HappyMeasure.zip"
SHA256 = "b" * 64


def test_is_frozen_app_returns_false_in_dev() -> None:
    assert is_frozen_app() is False


def test_default_install_dir_returns_cwd_in_dev() -> None:
    result = default_install_dir()
    assert result == Path.cwd().resolve()


def test_build_powershell_updater_script_custom_preserved_names(tmp_path: Path) -> None:
    custom_names = {"custom_folder", "another_folder"}
    script = build_powershell_updater_script(
        asset_url=ASSET_URL,
        target_dir=tmp_path,
        latest_version="v1.1b3",
        expected_sha256=SHA256,
        preserved_names=custom_names,
    )
    assert "custom_folder" in script
    assert "another_folder" in script
    assert "Invoke-WebRequest" in script


def test_build_powershell_updater_script_custom_app_exe(tmp_path: Path) -> None:
    script = build_powershell_updater_script(
        asset_url=ASSET_URL,
        target_dir=tmp_path,
        latest_version="v1.1b3",
        expected_sha256=SHA256,
        app_exe_name="CustomApp.exe",
    )
    assert "CustomApp.exe" in script


def test_write_updater_script_returns_launch_plan(tmp_path: Path) -> None:
    plan = write_powershell_updater_script(
        asset_url=ASSET_URL,
        target_dir=tmp_path,
        latest_version="v1.1b3",
        expected_sha256=SHA256,
    )
    assert isinstance(plan, UpdateLaunchPlan)
    assert plan.script_path.exists()
    assert plan.target_dir == tmp_path.resolve()
    assert plan.asset_url == ASSET_URL
    assert plan.latest_version == "v1.1b3"
    assert plan.expected_sha256 == SHA256


def test_launch_update_installer_raises_on_empty_url() -> None:
    import pytest
    with pytest.raises(ValueError, match="Missing release asset"):
        launch_update_installer(asset_url="", latest_version="v1.1b3", expected_sha256=SHA256)


def test_updater_rejects_unofficial_url_and_missing_digest(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="official GitHub repository"):
        build_powershell_updater_script(
            asset_url="https://example.invalid/release.zip",
            target_dir=tmp_path,
            latest_version="v1.1b3",
            expected_sha256=SHA256,
        )
    with pytest.raises(ValueError, match="valid SHA-256"):
        build_powershell_updater_script(
            asset_url=ASSET_URL,
            target_dir=tmp_path,
            latest_version="v1.1b3",
            expected_sha256="",
        )


def test_launch_update_installer_returns_plan(tmp_path: Path) -> None:
    with patch("keith_ivt.services.update_installer.subprocess.Popen") as mock_popen:
        plan = launch_update_installer(
            asset_url=ASSET_URL,
            target_dir=tmp_path,
            latest_version="v1.1b3",
            expected_sha256=SHA256,
        )
        assert isinstance(plan, UpdateLaunchPlan)
        mock_popen.assert_called_once()


def test_launch_update_installer_default_target_dir() -> None:
    with patch("keith_ivt.services.update_installer.subprocess.Popen") as mock_popen:
        with patch("keith_ivt.services.update_installer.default_install_dir") as mock_dir:
            mock_dir.return_value = Path("/fake/dir")
            plan = launch_update_installer(
                asset_url=ASSET_URL,
                latest_version="v1.1b3",
                expected_sha256=SHA256,
            )
            assert isinstance(plan, UpdateLaunchPlan)


def test_preserved_names_contains_expected_folders() -> None:
    assert "config" in PRESERVED_NAMES
    assert "logs" in PRESERVED_NAMES
    assert "exports" in PRESERVED_NAMES
    assert "backups" in PRESERVED_NAMES
    assert "cache" in PRESERVED_NAMES
    assert "data" in PRESERVED_NAMES


def test_update_launch_plan_fields() -> None:
    plan = UpdateLaunchPlan(
        script_path=Path("/tmp/script.ps1"),
        target_dir=Path("/tmp/target"),
        asset_url=ASSET_URL,
        latest_version="v1.1b3",
        expected_sha256=SHA256,
    )
    assert plan.script_path == Path("/tmp/script.ps1")
    assert plan.target_dir == Path("/tmp/target")
    assert plan.asset_url == ASSET_URL
    assert plan.latest_version == "v1.1b3"
    assert plan.expected_sha256 == SHA256
