from __future__ import annotations

import logging
import threading
import time
import webbrowser
from tkinter import messagebox

from keith_ivt.services.update_check import check_github_release
from keith_ivt.services.update_installer import launch_update_installer
from keith_ivt.version import __version__


class UpdateControllerMixin:
    """Non-blocking GitHub release metadata checks for the UI shell.

    The mixin reads release metadata and can hand off installation to an
    external updater after explicit user confirmation.  The app itself never
    overwrites files while it is running.
    """

    UPDATE_OWNER = "Xiaolong-6"
    UPDATE_REPO = "HappyMeasure"
    UPDATE_REPO_URL = "https://github.com/Xiaolong-6/HappyMeasure"
    UPDATE_CHECK_CACHE_SECONDS = 30 * 60

    def _default_update_status_message(self) -> str:
        return "Update status: not checked yet. Manual upgrade remains available from the release page."

    def _set_update_check_message(self, message: str) -> None:
        text = (message or "").strip() or self._default_update_status_message()
        if hasattr(self, "update_status_text"):
            self.update_status_text.set(text)
        if hasattr(self, "update_notice_text"):
            self.update_notice_text.set(text)

    def _check_for_updates_async(self, prompt_install: bool = False) -> None:
        """Start a non-blocking GitHub release metadata check."""
        if self._has_fresh_update_check_result():
            self._handle_update_check_result(
                self._last_update_check_result,
                from_cache=True,
                prompt_install=prompt_install,
            )
            return
        if self._update_check_in_progress:
            self._set_update_check_message("Checking for updates...")
            return
        self._set_update_check_message("Checking for updates...")
        self._update_check_in_progress = True
        threading.Thread(target=lambda: self._check_for_updates_worker(prompt_install=prompt_install), daemon=True).start()

    def _check_for_updates_worker(self, prompt_install: bool = False) -> None:
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
                "asset_name": None,
                "asset_download_url": None,
                "asset_sha256": None,
            }
        self.root.after(0, lambda result=result: self._handle_update_check_result(result, prompt_install=prompt_install))

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
        prompt_install: bool = False,
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
            self._set_update_check_message(message)
            if not from_cache:
                self.log_event(message)
            if prompt_install:
                self._prompt_for_update_install(result)
        elif status == "offline":
            self._set_update_check_message("No network. Update status unknown; open the release page to check manually.")
        elif status == "error":
            self._set_update_check_message("Update check unavailable. Open the release page to check manually.")
            logging.getLogger("keith_ivt.ui.updates").warning(message)
        elif status == "ahead":
            latest = result.get("latest_version") or "unknown"
            self._set_update_check_message(
                f"Local beta is newer than the latest published release ({latest})."
            )
        elif status == "current":
            latest = result.get("latest_version") or __version__
            self._set_update_check_message(f"You are up to date ({latest}).")
        else:
            self._set_update_check_message("Update status: not checked yet. Manual upgrade remains available from the release page.")

    def _prompt_for_update_install(self, result: dict[str, str | None]) -> None:
        latest = result.get("latest_version") or "the latest version"
        asset_url = result.get("asset_download_url")
        asset_sha256 = result.get("asset_sha256")
        asset_name = result.get("asset_name") or "HappyMeasure Windows portable zip"
        if not asset_url or not asset_sha256:
            if messagebox.askyesno(
                "Update available",
                f"{latest} is available, but no cryptographically verifiable Windows portable "
                "package was found.\n\nOpen the release page?",
            ):
                self._open_update_release_page()
            return
        busy_states = {"preparing", "running", "paused", "stopping"}
        if getattr(self, "_run_state", "idle") in busy_states:
            messagebox.showinfo(
                "Update available",
                "A new version is available, but installation is disabled while a measurement is running. Stop the sweep before updating.",
            )
            return
        question = (
            f"New HappyMeasure version available: {latest}\n\n"
            f"Release package: {asset_name}\n\n"
            "Download and install now? Your settings, presets, logs, exports, backups, and data folders will be kept."
        )
        if messagebox.askyesno("Install update", question):
            self._start_update_install(result)

    def _start_update_install(self, result: dict[str, str | None]) -> None:
        try:
            plan = launch_update_installer(
                asset_url=str(result.get("asset_download_url") or ""),
                latest_version=str(result.get("latest_version") or "unknown"),
                expected_sha256=str(result.get("asset_sha256") or ""),
            )
        except Exception as exc:
            logging.getLogger("keith_ivt.ui.updates").exception("Failed to launch updater")
            messagebox.showerror("Update failed", f"Could not start the updater:\n{exc}")
            return
        self.log_event(f"Updater launched for {plan.latest_version}: {plan.script_path}")
        messagebox.showinfo("Updater started", "HappyMeasure will close now. The updater will download and install the new version, then restart the app.")
        try:
            self.root.after(100, self.root.destroy)
        except Exception:
            pass

    def _open_update_release_page(self) -> None:
        try:
            webbrowser.open(self._update_release_url or self.UPDATE_REPO_URL)
        except Exception as exc:
            logging.getLogger("keith_ivt.ui.updates").warning("Failed to open release page: %s", exc)

    def _check_for_updates(self) -> None:
        """Compatibility hook retained for callers that still request a check."""
        self._check_for_updates_async(prompt_install=False)
