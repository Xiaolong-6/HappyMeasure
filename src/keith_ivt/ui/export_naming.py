from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from keith_ivt.models import SweepResult

_SAFE_RE = re.compile(r"[^A-Za-z0-9._+-]+")


def safe_token(value: object, fallback: str = "item", max_len: int = 24) -> str:
    text = str(value or "").strip() or fallback
    text = _SAFE_RE.sub("-", text).strip("-_.") or fallback
    return text[:max_len].strip("-_.") or fallback


def _compact_num(value: float) -> str:
    try:
        v = float(value)
    except Exception:
        return "x"
    return f"{v:.3g}".replace("+", "").replace("-", "m").replace(".", "p")


def compact_result_tag(result: SweepResult | None, fallback: str = "data") -> str:
    if result is None:
        return fallback
    cfg = result.config
    device = safe_token(cfg.device_name, "device", 18)
    operator = safe_token(cfg.operator, "", 12)
    mode = "Isrc" if getattr(cfg.mode, "value", cfg.mode) == "CURR" else "Vsrc"
    kind_raw = str(getattr(cfg.sweep_kind, "value", cfg.sweep_kind)).upper()
    kind = {"STEP": "step", "TIME": "time", "ADAPTIVE": "adapt"}.get(kind_raw, safe_token(kind_raw, "sweep", 8))
    npts = len(result.points)
    if kind == "time":
        sweep = f"time-{_compact_num(getattr(cfg, 'constant_value', 0.0))}"
    elif kind == "adapt":
        sweep = f"adapt-{npts}pts"
    else:
        sweep = f"{_compact_num(cfg.start)}to{_compact_num(cfg.stop)}"
    parts = [device]
    if operator:
        parts.append(f"op-{operator}")
    parts.extend([mode, kind, sweep, f"{npts}pts"])
    return "_".join(parts)


def suggested_single_csv_name(result: SweepResult, trace_name: str | None = None, max_len: int = 96) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = compact_result_tag(result)
    if trace_name:
        tag = safe_token(trace_name, "device", 18) + tag[tag.find("_"):]
    return _trim_filename(f"HM_{stamp}_{tag}.csv", max_len)


def suggested_all_csv_name(results: Iterable[SweepResult], max_len: int = 96) -> str:
    results = list(results)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    count = len(results)
    if not results:
        return _trim_filename(f"HM_{stamp}_all-0.csv", max_len)
    modes = sorted({"Isrc" if r.config.mode.value == "CURR" else "Vsrc" for r in results})
    kinds = sorted({str(r.config.sweep_kind.value).lower() for r in results})
    first_device = safe_token(results[0].config.device_name, "device", 16)
    tag = f"all-{count}_{'+'.join(modes)}_{'+'.join(kinds)}_{first_device}"
    return _trim_filename(f"HM_{stamp}_{tag}.csv", max_len)


def suggested_figure_name(max_len: int = 96, ext: str = ".png") -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _trim_filename(f"HM_{stamp}_plot{ext}", max_len)


def _trim_filename(name: str, max_len: int) -> str:
    if len(name) <= max_len:
        return name
    stem, dot, suffix = name.rpartition(".")
    if not dot:
        return name[:max_len]
    keep = max_len - len(suffix) - 1
    return f"{stem[:keep].rstrip('-_.')}.{suffix}"
