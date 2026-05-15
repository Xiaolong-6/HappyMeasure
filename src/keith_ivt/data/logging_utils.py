from __future__ import annotations

from datetime import datetime
from pathlib import Path

from keith_ivt.data.settings import clamp_log_max_bytes


class AppLog:
    """Small rotating text log for offline-alpha UI state messages."""

    def __init__(self, path: str | Path = "logs/log.txt", max_bytes: int = 1_000_000) -> None:
        self.path = Path(path)
        self.max_bytes = clamp_log_max_bytes(max_bytes)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def set_max_bytes(self, max_bytes: int) -> None:
        self.max_bytes = clamp_log_max_bytes(max_bytes)
        # Apply a newly lowered KB limit immediately.  Without this, changing
        # the setting looked like it did nothing until a later write crossed
        # the old file size.
        self._rotate_if_needed(0)

    def _rotated_path(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return self.path.with_name(f"log_{stamp}.txt")

    def _rotate_if_needed(self, incoming_bytes: int = 0) -> None:
        """Rotate before a write would exceed the configured max size.

        The previous implementation only checked the existing file before the
        append, so a write that crossed the limit left logs/log.txt larger than
        the requested max until the *next* event.  This method enforces the
        limit for the current write whenever possible.
        """
        if not self.path.exists():
            return
        try:
            current = self.path.stat().st_size
        except OSError:
            return
        if current > 0 and current + max(0, incoming_bytes) > self.max_bytes:
            self.path.replace(self._rotated_path())

    def write(self, message: str) -> str:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{stamp}] {message}"
        incoming = len((line + "\n").encode("utf-8"))
        self._rotate_if_needed(incoming)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        # A single line can be larger than max_bytes.  Keep that line rather
        # than rotating it away immediately, but future writes will rotate.
        return line

    def tail(self, max_lines: int = 80) -> list[str]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-max_lines:]
