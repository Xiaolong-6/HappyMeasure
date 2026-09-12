from __future__ import annotations

from keith_ivt.diagnostics.runtime_logging import TeeTextIO


def test_tee_text_io_handles_missing_original_stream(tmp_path) -> None:
    log_path = tmp_path / "console.log"
    with log_path.open("w", encoding="utf-8") as handle:
        tee = TeeTextIO(None, handle)
        assert tee.write("hello\n") == 6
        tee.flush()

    assert log_path.read_text(encoding="utf-8") == "hello\n"
