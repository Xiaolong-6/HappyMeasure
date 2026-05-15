from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_alpha7_queue_drain_is_bounded_for_pause_stop_responsiveness():
    src = read("src/keith_ivt/ui/sweep_controller.py")
    process = src[src.index("def _process_queue"):src.index("def _handle_complete")]
    assert "max_messages = 40" in process
    assert "while processed < max_messages" in process
    assert "redraw_live = True" in process
    assert "self._redraw_all_plots(live_only=True)" in process
    assert "self.root.after(35 if processed >= max_messages else 100" in process
    # Critical contract: no per-point redraw inside the point branch.
    point_branch = process[process.index('if kind == "point"'):process.index('elif kind == "complete"')]
    assert "_redraw_all_plots" not in point_branch


def test_alpha7_adaptive_table_is_responsive_segment_rows():
    src = read("src/keith_ivt/ui/sweep_config.py")
    table = src[src.index("def _build_adaptive_segment_table"):src.index("def _add_adaptive_row")]
    assert "compact adaptive segment editor" in table
    assert 'uniform="adaptive_compact"' in table
    assert "minsize=72" in table
    assert "＋ Row" in table and "－ Row" in table and "Reset" in table
    assert "Duplicate boundaries are removed automatically" in table


def test_alpha7_docs_mention_pause_stop_and_adaptive_table_hotfix():
    changelog = read("docs/CHANGELOG.md")
    handoff = read("docs/AGENT_HANDOFF.md")
    assert "0.5.0-alpha.1" in changelog
    assert "Pause/Stop" in changelog
    assert "adaptive" in changelog.lower()
    assert "bounded UI queue" in handoff or "bounded queue" in handoff
