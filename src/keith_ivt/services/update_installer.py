from __future__ import annotations

import subprocess
import sys
import tempfile
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

PRESERVED_NAMES = {
    "config",
    "logs",
    "exports",
    "backups",
    "cache",
    "data",
}

PROGRAM_FILE_HINTS = {
    "HappyMeasure.exe",
    "README.md",
    "NOTICE.md",
    "Run_HappyMeasure.bat",
    "Run_HappyMeasure.ps1",
}


@dataclass(frozen=True)
class UpdateLaunchPlan:
    script_path: Path
    target_dir: Path
    asset_url: str
    latest_version: str
    expected_sha256: str


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def default_install_dir() -> Path:
    """Return the portable app folder that should be replaced by the updater."""
    if is_frozen_app():
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def _ps_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _preserve_list(names: Iterable[str] = PRESERVED_NAMES) -> str:
    return "@(" + ", ".join(_ps_single_quoted(str(name)) for name in sorted(set(names))) + ")"


def _validate_release_asset(asset_url: str, expected_sha256: str) -> tuple[str, str]:
    parsed = urlparse(asset_url)
    expected_prefix = "/Xiaolong-6/HappyMeasure/releases/download/"
    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname is None
        or parsed.hostname.lower() != "github.com"
        or not parsed.path.lower().startswith(expected_prefix.lower())
    ):
        raise ValueError(
            "Update asset must be an HTTPS release download from the official GitHub repository."
        )
    digest = expected_sha256.strip().lower().removeprefix("sha256:")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("A valid SHA-256 digest is required before installing an update.")
    return asset_url, digest


def build_powershell_updater_script(
    *,
    asset_url: str,
    target_dir: Path,
    latest_version: str,
    expected_sha256: str,
    app_exe_name: str = "HappyMeasure.exe",
    preserved_names: Iterable[str] = PRESERVED_NAMES,
) -> str:
    """Create the external PowerShell updater used by the packaged app.

    The script intentionally runs outside HappyMeasure.exe so Windows file locks
    do not prevent replacement.  It downloads the portable zip, extracts it to a
    staging directory, deletes only old program files, keeps user folders in
    place, copies the new program files into the original folder, and restarts
    the app.
    """
    asset_url, expected_sha256 = _validate_release_asset(asset_url, expected_sha256)
    target = str(Path(target_dir).resolve())
    preserve = _preserve_list(preserved_names)
    script = f"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$AssetUrl = {_ps_single_quoted(asset_url)}
$TargetDir = {_ps_single_quoted(target)}
$LatestVersion = {_ps_single_quoted(latest_version)}
$ExpectedSha256 = {_ps_single_quoted(expected_sha256)}
$AppExeName = {_ps_single_quoted(app_exe_name)}
$PreserveNames = {preserve}
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$WorkRoot = Join-Path $env:TEMP ("HappyMeasureUpdate_" + $Stamp)
$ZipPath = Join-Path $WorkRoot "release.zip"
$StageDir = Join-Path $WorkRoot "stage"
$BackupRoot = Join-Path $TargetDir "backups"
$BackupDir = Join-Path $BackupRoot ("update_" + $Stamp)

New-Item -ItemType Directory -Force -Path $WorkRoot, $StageDir, $BackupRoot | Out-Null
Start-Sleep -Seconds 2

Invoke-WebRequest -Uri $AssetUrl -OutFile $ZipPath -UseBasicParsing
$ActualSha256 = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualSha256 -ne $ExpectedSha256) {{
    throw "Downloaded update failed SHA-256 verification."
}}
Expand-Archive -Path $ZipPath -DestinationPath $StageDir -Force

$SourceRoot = $StageDir
$NestedExe = Get-ChildItem -Path $StageDir -Filter $AppExeName -Recurse -File | Select-Object -First 1
if ($null -eq $NestedExe) {{
    throw "Downloaded update does not contain $AppExeName."
}}
$SourceRoot = $NestedExe.Directory.FullName

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$MoveCompleted = $false
try {{
    Get-ChildItem -LiteralPath $TargetDir -Force | ForEach-Object {{
        if ($PreserveNames -contains $_.Name) {{ return }}
        Move-Item -LiteralPath $_.FullName -Destination $BackupDir -Force
    }}
    $MoveCompleted = $true
    Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {{
        if ($PreserveNames -contains $_.Name) {{ return }}
        Copy-Item -LiteralPath $_.FullName -Destination $TargetDir -Recurse -Force
    }}
    $NewExe = Join-Path $TargetDir $AppExeName
    if (-not (Test-Path -LiteralPath $NewExe -PathType Leaf)) {{
        throw "Installed update does not contain $AppExeName."
    }}
}} catch {{
    $UpdateError = $_
    if ($MoveCompleted) {{
        Get-ChildItem -LiteralPath $TargetDir -Force | ForEach-Object {{
            if ($PreserveNames -contains $_.Name) {{ return }}
            Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }}
    }}
    Get-ChildItem -LiteralPath $BackupDir -Force | ForEach-Object {{
        Copy-Item -LiteralPath $_.FullName -Destination $TargetDir -Recurse -Force
    }}
    throw $UpdateError
}}

$NewExe = Join-Path $TargetDir $AppExeName
Start-Process -FilePath $NewExe -WorkingDirectory $TargetDir
""".strip() + "\n"
    return script


def write_powershell_updater_script(
    *,
    asset_url: str,
    target_dir: Path | None = None,
    latest_version: str,
    expected_sha256: str,
) -> UpdateLaunchPlan:
    target = (target_dir or default_install_dir()).resolve()
    update_dir = Path(tempfile.mkdtemp(prefix="HappyMeasureUpdater_"))
    script_path = update_dir / "happymeasure_update.ps1"
    script_path.write_text(
        build_powershell_updater_script(
            asset_url=asset_url,
            target_dir=target,
            latest_version=latest_version,
            expected_sha256=expected_sha256,
        ),
        encoding="utf-8",
    )
    return UpdateLaunchPlan(
        script_path=script_path,
        target_dir=target,
        asset_url=asset_url,
        latest_version=latest_version,
        expected_sha256=expected_sha256.strip().lower().removeprefix("sha256:"),
    )


def launch_update_installer(
    *,
    asset_url: str,
    target_dir: Path | None = None,
    latest_version: str,
    expected_sha256: str,
) -> UpdateLaunchPlan:
    """Write and launch the external updater, returning the launch plan."""
    if not asset_url:
        raise ValueError("Missing release asset download URL")
    plan = write_powershell_updater_script(
        asset_url=asset_url,
        target_dir=target_dir,
        latest_version=latest_version,
        expected_sha256=expected_sha256,
    )
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(plan.script_path),
    ]
    subprocess.Popen(cmd, cwd=str(plan.target_dir), close_fds=True)
    return plan


__all__ = [
    "PRESERVED_NAMES",
    "UpdateLaunchPlan",
    "build_powershell_updater_script",
    "default_install_dir",
    "is_frozen_app",
    "launch_update_installer",
    "write_powershell_updater_script",
]
