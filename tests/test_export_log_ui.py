from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keith_ivt.data.exporters import result_metadata, save_combined_csv, save_csv
from keith_ivt.data.importers import load_csv
from keith_ivt.data.logging_utils import AppLog
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui.export_naming import suggested_all_csv_name, suggested_single_csv_name

def _result(name="Device_A", operator="XL", y_scale=1.0):
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.2,
        step=0.1,
        compliance=0.01,
        nplc=1.0,
        device_name=name,
        operator=operator,
        sweep_kind=SweepKind.STEP,
    )
    pts = [SweepPoint(0.0, 0.0), SweepPoint(0.1, 1e-5 * y_scale), SweepPoint(0.2, 2e-5 * y_scale)]
    return SweepResult(cfg, pts)


def test_metadata_fingerprint_distinguishes_same_name_different_data():
    a = _result(y_scale=1.0)
    b = _result(y_scale=2.0)
    ma = result_metadata(a)
    mb = result_metadata(b)
    assert ma["device_name"] == mb["device_name"]
    assert ma["operator"] == "XL"
    assert ma["data_fingerprint"] != mb["data_fingerprint"]
    assert ma["trace_uid"] != mb["trace_uid"]


def test_single_and_combined_csv_v2_roundtrip_with_operator(tmp_path: Path):
    one = _result("D1", "Alice", 1.0)
    two = _result("D2", "Bob", 2.0)
    single_path = tmp_path / "single.csv"
    save_csv(one, single_path)
    text = single_path.read_text(encoding="utf-8")
    assert "# schema,single-v2" in text
    assert "data_fingerprint" in text
    assert load_csv(single_path)[0].config.operator == "Alice"

    combined_path = tmp_path / "all.csv"
    save_combined_csv([one, two], combined_path)
    combined = combined_path.read_text(encoding="utf-8")
    assert "# section,trace_metadata" in combined
    assert "trace_index,device_name,operator" in combined
    assert "# section,data" in combined
    assert "T001 D1 · Alice" in combined
    loaded = load_csv(combined_path)
    assert [r.config.device_name for r in loaded] == ["D1", "D2"]
    assert [r.config.operator for r in loaded] == ["Alice", "Bob"]
    assert [len(r.points) for r in loaded] == [3, 3]


def test_export_filename_is_compact_but_informative():
    r = _result("Long Device Name With Spaces", "XL", 1.0)
    single = suggested_single_csv_name(r)
    all_name = suggested_all_csv_name([r, _result("D2", "YL", 2.0)])
    assert single.startswith("HM_") and single.endswith(".csv")
    assert "op-XL" in single
    assert "Vsrc" in single
    assert "step" in single
    assert len(single) <= 96
    assert "all-2" in all_name and "Vsrc" in all_name and len(all_name) <= 96


def test_log_rotation_kb_threshold_creates_new_file(tmp_path: Path):
    log = AppLog(path=tmp_path / "log.txt", max_bytes=10_000)
    log.write("x" * 9990)
    log.write("cross threshold")
    rotated = list(tmp_path.glob("log_*.txt"))
    assert rotated
    assert (tmp_path / "log.txt").read_text(encoding="utf-8").strip().endswith("cross threshold")


def test_alpha7_ui_contracts_are_present():
    simple = (ROOT / "src/keith_ivt/ui/simple_app.py").read_text(encoding="utf-8")
    panels = (ROOT / "src/keith_ivt/ui/panels.py").read_text(encoding="utf-8")
    operator = (ROOT / "src/keith_ivt/ui/operator_bar.py").read_text(encoding="utf-8")
    trace_panel = (ROOT / "src/keith_ivt/ui/trace_panel.py").read_text(encoding="utf-8")
    plot_panel = (ROOT / "src/keith_ivt/ui/plot_panel.py").read_text(encoding="utf-8")
    sweep = (ROOT / "src/keith_ivt/ui/sweep_config.py").read_text(encoding="utf-8")
    assert 'StringVar(value=getattr(self.settings, "ui_font_family", "Verdana"))' in simple
    assert "Log max KB" in panels
    assert 'text="STOP"' in operator
    assert "\"operator\": (\"Operator\"" in plot_panel or "'operator': ('Operator'" in plot_panel
    assert 'pack_configure(fill="both" if kind == SweepKind.ADAPTIVE.value else "x"' in sweep
