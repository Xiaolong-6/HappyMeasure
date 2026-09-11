from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.services.update_check import parse_version


def test_beta_version_compares_ahead_of_old_alpha_release() -> None:
    assert parse_version("1.0b1") > parse_version("v0.7a1")


def test_update_controller_has_local_ahead_copy() -> None:
    text = (SRC / "keith_ivt" / "ui" / "update_controller.py").read_text(encoding="utf-8")
    assert 'status == "ahead"' in text
    assert "Local beta is newer than the latest published release" in text
