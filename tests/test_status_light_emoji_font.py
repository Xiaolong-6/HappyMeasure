from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_status_light_uses_fixed_color_emoji_font_style() -> None:
    theme = (ROOT / "src" / "keith_ivt" / "ui" / "theme.py").read_text(encoding="utf-8")
    status_bar = (ROOT / "src" / "keith_ivt" / "ui" / "status_bar.py").read_text(encoding="utf-8")
    bridge = (ROOT / "src" / "keith_ivt" / "ui" / "app_state_bridge.py").read_text(encoding="utf-8")

    assert 'emoji_font = ("Segoe UI Emoji", 12)' in theme
    assert 'self.style.configure("ConnRed.TLabel"' in theme
    assert 'self.style.configure("ConnGreen.TLabel"' in theme
    assert 'font=emoji_font' in theme
    assert 'style="ConnRed.TLabel"' in status_bar
    assert '"😈" if state is ConnectionState.SIMULATED else "🟢" if state is ConnectionState.CONNECTED else "🔴"' in bridge
