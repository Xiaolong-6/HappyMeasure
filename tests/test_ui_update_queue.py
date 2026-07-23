from __future__ import annotations

from queue import Queue

import keith_ivt.ui.update_controller as update_controller
from keith_ivt.ui.update_controller import UpdateControllerMixin


def test_background_update_worker_uses_ui_event_queue(monkeypatch) -> None:
    result = {
        "status": "current",
        "message": "Up to date",
        "latest_version": "1.0",
        "release_url": None,
        "asset_name": None,
        "asset_download_url": None,
        "asset_sha256": None,
    }
    monkeypatch.setattr(
        update_controller,
        "check_github_release",
        lambda *_args, **_kwargs: result,
    )
    controller = UpdateControllerMixin()
    controller._queue = Queue()

    controller._check_for_updates_worker(prompt_install=True)

    kind, payload = controller._queue.get_nowait()
    assert kind == "update_check"
    assert payload == (result, True)
