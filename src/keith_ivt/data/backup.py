from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from keith_ivt.data.exporters import save_csv
from keith_ivt.models import SweepResult


def safe_filename(text: str, fallback: str = "Device") -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", text.strip()).strip("._")
    return clean or fallback


def default_backup_dir(project_root: Path | None = None) -> Path:
    base = project_root or Path.cwd()
    return base / "backups" / "auto"


def autosave_result(result: SweepResult, backup_dir: str | Path | None = None) -> Path:
    directory = Path(backup_dir) if backup_dir is not None else default_backup_dir()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    device = safe_filename(result.config.device_name)
    filename = f"{stamp}_{device}_{result.config.mode.value}_backup.csv"
    return save_csv(result, directory / filename)
