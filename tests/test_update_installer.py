from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.services.update_installer import (
    PRESERVED_NAMES,
    build_powershell_updater_script,
    write_powershell_updater_script,
)

ASSET_URL = "https://github.com/Xiaolong-6/HappyMeasure/releases/download/v1.1b3/HappyMeasure.zip"
SHA256 = "a" * 64


def test_updater_script_preserves_user_data_and_downloads_asset(tmp_path: Path) -> None:
    script = build_powershell_updater_script(
        asset_url=ASSET_URL,
        target_dir=tmp_path,
        latest_version="v1.1b1",
        expected_sha256=SHA256,
    )
    assert "Invoke-WebRequest" in script
    assert "Expand-Archive" in script
    assert "Get-FileHash" in script
    assert "HappyMeasure.exe" in script
    for name in PRESERVED_NAMES:
        assert f"'{name}'" in script
    assert "Move-Item" in script
    assert "Copy-Item" in script
    assert "Start-Process" in script


def test_write_updater_script_creates_external_script(tmp_path: Path) -> None:
    plan = write_powershell_updater_script(
        asset_url=ASSET_URL,
        target_dir=tmp_path,
        latest_version="v1.1b1",
        expected_sha256=SHA256,
    )
    assert plan.script_path.exists()
    assert plan.target_dir == tmp_path.resolve()
    content = plan.script_path.read_text(encoding="utf-8")
    assert ASSET_URL in content
    assert str(tmp_path.resolve()) in content
