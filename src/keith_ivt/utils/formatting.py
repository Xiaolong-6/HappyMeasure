from __future__ import annotations

import math

_PREFIXES = [
    (-12, "p"),
    (-9, "n"),
    (-6, "µ"),
    (-3, "m"),
    (0, ""),
    (3, "k"),
    (6, "M"),
    (9, "G"),
]


def format_si(value: float, unit: str = "", precision: int = 3) -> str:
    try:
        x = float(value)
    except Exception:
        return f"{value} {unit}".strip()
    if math.isnan(x) or math.isinf(x):
        return f"{x:g} {unit}".strip()
    if x == 0:
        return f"0 {unit}".strip()
    exp = int(math.floor(math.log10(abs(x)) / 3) * 3)
    exp = max(min(exp, 9), -12)
    prefix = dict(_PREFIXES).get(exp, "")
    scaled = x / (10 ** exp)
    return f"{scaled:.{precision}g} {prefix}{unit}".strip()


def format_voltage(value: float, precision: int = 3) -> str:
    return format_si(value, "V", precision)


def format_current(value: float, precision: int = 3) -> str:
    return format_si(value, "A", precision)


def format_resistance(value: float, precision: int = 3) -> str:
    return format_si(value, "Ω", precision)
