from __future__ import annotations

import math
from typing import Any


def logspace(start: float, stop: float, count: int) -> list[float]:
    """Return logarithmically spaced values preserving the sign when possible.

    This helper is intentionally simple for the offline alpha adaptive sweep. It
    supports positive ranges directly. For negative ranges use -logspace(...),
    or define values explicitly in the logic editor.
    """
    start = float(start)
    stop = float(stop)
    count = int(count)
    if count <= 0:
        raise ValueError("count must be positive")
    if start <= 0 or stop <= 0:
        raise ValueError("logspace start/stop must be positive")
    if count == 1:
        return [start]
    a = math.log10(start)
    b = math.log10(stop)
    return [10 ** (a + (b - a) * i / (count - 1)) for i in range(count)]


def linspace(start: float, stop: float, count: int) -> list[float]:
    count = int(count)
    if count <= 0:
        raise ValueError("count must be positive")
    if count == 1:
        return [float(start)]
    return [float(start) + (float(stop) - float(start)) * i / (count - 1) for i in range(count)]


def dedupe_adjacent_values(values: list[float], tolerance: float = 1e-15) -> list[float]:
    """Remove adjacent duplicate source values, mainly at adaptive segment joins.

    This preserves intentional repeated values in non-adjacent positions while
    avoiding duplicate boundary points such as 0->1 followed by 1->2.
    """
    cleaned: list[float] = []
    for value in values:
        f = float(value)
        if cleaned and abs(cleaned[-1] - f) <= tolerance:
            continue
        cleaned.append(f)
    return cleaned

_ALLOWED_GLOBALS: dict[str, Any] = {
    "__builtins__": {},
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "range": range,
    "len": len,
    "float": float,
    "int": int,
    "sum": sum,
    "math": math,
    "logspace": logspace,
    "linspace": linspace,
}


def adaptive_values_from_logic(logic: str) -> list[float]:
    """Evaluate a small alpha-stage adaptive sweep expression.

    Contract: the user logic must assign a variable named ``values`` to a list
    of numeric source values. This is not exposed as a remote/sandboxed service;
    it is an offline internal alpha helper for local instrument-control scripts.
    """
    local_ns: dict[str, Any] = {}
    code = (logic or "").strip()
    if not code:
        raise ValueError("Adaptive logic is empty. Define values = [...].")
    exec(code, _ALLOWED_GLOBALS, local_ns)
    if "values" not in local_ns:
        raise ValueError("Adaptive logic must define a variable named values.")
    raw = local_ns["values"]
    try:
        values = [float(x) for x in list(raw)]
    except Exception as exc:
        raise ValueError("Adaptive values must be a numeric iterable.") from exc
    values = dedupe_adjacent_values(values)
    if not values:
        raise ValueError("Adaptive logic produced no values.")
    if len(values) > 100_000:
        raise ValueError("Adaptive logic produced too many values for alpha UI.")
    return values


from keith_ivt.core.adaptive_rules import default_log_rule, logic_from_rule

DEFAULT_ADAPTIVE_LOGIC = logic_from_rule(default_log_rule())
