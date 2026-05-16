from __future__ import annotations

import logging
import threading
import time
import webbrowser

from keith_ivt.services.update_check import check_github_release
from keith_ivt.version import __version__


class UpdateControllerMixin:
    """Non-blocking GitHub release metadata checks for the UI shell.

    The mixin only reads release metadata and surfaces a manual-upgrade notice.
    It never downloads, installs, or replaces files.
    """

    UPDATE_OWNER = "Xiaolong-6"
    UPDATE_REPO = "HappyMeasure"
    UPDATE_REPO_URL = "https://github.com/Xiaolong-6/HappyMeasure"
    UPDATE_CHECK_CACHE_SECONDS = 30 * 60

    def _check_for_updates_async(self) -> None:
        """Start a non-blocking GitHub release metadata check."""
        if self._has_fresh_update_check_result():
            self._handle_update_check_result(self._last_update_check_result, from_cache=True)
            return
        if self._update_check_in_progress:
            return
        self._update_check_in_progress = True
        threading.Thread(target=self._check_for_updates_worker, daemon=True).start()

    def _check_for_updates_worker(self) -> None:
        try:
            result = check_github_release(
                self.UPDATE_OWNER,
                self.UPDATE_REPO,
                __version__,
                include_prerelease=True,
                timeout_s=3.0,
            )
        except Exception as exc:
            result = {
                "status": "error",
                "message": f"Update check unavailable: {exc}",
                "latest_version": None,
                "release_url": None,
            }
        self.root.after(0, lambda result=result: self._handle_update_check_result(result))

    def _has_fresh_update_check_result(self) -> bool:
        if self._last_update_check_result is None or self._last_update_check_timestamp is None:
            return False
        age_s = time.monotonic() - self._last_update_check_timestamp
        return age_s < self.UPDATE_CHECK_CACHE_SECONDS

    def _show_cached_update_check_result(self) -> bool:
        if not self._last_update_check_result:
            return False
        self._handle_update_check_result(self._last_update_check_result, from_cache=True)
        return True

    def _handle_update_check_result(
        self,
        result: dict[str, str | None] | None,
        from_cache: bool = False,
    ) -> None:
        if result is None:
            return
        if not from_cache:
            self._update_check_in_progress = False
            self._last_update_check_result = result
            self._last_update_check_timestamp = time.monotonic()
        status = result.get("status")
        message = result.get("message") or "Update check unavailable."
        release_url = result.get("release_url")
        if release_url:
            self._update_release_url = release_url

        if status == "newer":
            self.update_notice_text.set(message)
            self.update_status_text.set(message)
            if not from_cache:
                self.log_event(message)
        elif status == "offline":
            self.update_notice_text.set("Update check unavailable: offline.")
            self.update_status_text.set("Update check unavailable: offline.")
        elif status == "error":
            self.update_notice_text.set("Update check unavailable.")
            self.update_status_text.set("Update check unavailable.")
            logging.getLogger("keith_ivt.ui.updates").warning(message)
        else:
            self.update_notice_text.set("")
            self.update_status_text.set("")

    def _open_update_release_page(self) -> None:
        try:
            webbrowser.open(self._update_release_url or self.UPDATE_REPO_URL)
        except Exception as exc:
            logging.getLogger("keith_ivt.ui.updates").warning("Failed to open release page: %s", exc)

    def _check_for_updates(self) -> None:
        """Compatibility hook retained for callers that still request a check."""
        self._check_for_updates_async()
