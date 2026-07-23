from pathlib import Path


def test_preset_review_shows_hardware_common_and_active_parameters() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "keith_ivt"
        / "ui"
        / "settings_preset_actions.py"
    ).read_text(encoding="utf-8")
    review = source[source.index("def _fast_preset_review") : source.index("def save_named")]

    assert "[Hardware]" in review
    assert "COM port:" in review
    assert "Auto source range:" in review
    assert "Auto measure range:" in review
    assert "Hysteresis:" in review
    assert "Adaptive segments" in review
    assert "parameters.items()" in review


def test_snapshot_capture_does_not_parse_adaptive_or_include_other_pages() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "keith_ivt"
        / "ui"
        / "settings_preset_actions.py"
    ).read_text(encoding="utf-8")
    capture = source[
        source.index("def _current_preset_snapshot") : source.index(
            "def _current_sweep_preset_dict"
        )
    ]

    assert "_sync_adaptive_logic_text" not in capture
    assert '"segments": self._adaptive_segment_text()' in capture
    for unrelated in (
        "ui_theme",
        "log_max",
        "cache_enabled",
        "device_name",
        "operator",
        "arrangement",
    ):
        assert unrelated not in capture
