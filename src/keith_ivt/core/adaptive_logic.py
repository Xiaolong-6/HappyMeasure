from __future__ import annotations

import ast
import math

from keith_ivt.core.adaptive_rules import default_log_rule, logic_from_rule

MAX_ADAPTIVE_POINTS = 100_000
MAX_LOGIC_LENGTH = 100_000
MAX_AST_NODES = 200_000


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
    if count > MAX_ADAPTIVE_POINTS:
        raise ValueError(f"count must not exceed {MAX_ADAPTIVE_POINTS}")
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
    if count > MAX_ADAPTIVE_POINTS:
        raise ValueError(f"count must not exceed {MAX_ADAPTIVE_POINTS}")
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


def _numeric_literal(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _numeric_literal(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    raise ValueError("Adaptive values and function arguments must be numeric literals.")


def _evaluate_values_expression(node: ast.AST) -> list[float]:
    if isinstance(node, (ast.List, ast.Tuple)):
        if len(node.elts) > MAX_ADAPTIVE_POINTS:
            raise ValueError(f"Adaptive logic produced more than {MAX_ADAPTIVE_POINTS} values.")
        return [float(_numeric_literal(item)) for item in node.elts]

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in {"linspace", "logspace"}:
            raise ValueError(
                "Only linspace(start, stop, count) and logspace(start, stop, count) are allowed."
            )
        if node.keywords or len(node.args) != 3:
            raise ValueError(f"{node.func.id} requires exactly three positional arguments.")
        start = float(_numeric_literal(node.args[0]))
        stop = float(_numeric_literal(node.args[1]))
        count = int(_numeric_literal(node.args[2]))
        function = linspace if node.func.id == "linspace" else logspace
        return function(start, stop, count)

    raise ValueError("Adaptive logic must use a numeric list, linspace(...), or logspace(...).")


def _parse_values_expression(logic: str) -> ast.AST:
    try:
        tree = ast.parse(logic, mode="exec")
    except SyntaxError as exc:
        raise ValueError(f"Invalid adaptive logic syntax: {exc.msg}.") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise ValueError("Adaptive logic is too complex.")
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assign):
        raise ValueError("Adaptive logic must contain only one assignment to values.")
    assignment = tree.body[0]
    if (
        len(assignment.targets) != 1
        or not isinstance(assignment.targets[0], ast.Name)
        or assignment.targets[0].id != "values"
    ):
        raise ValueError("Adaptive logic must assign to a variable named values.")
    return assignment.value


def adaptive_values_from_logic(logic: str, *, remove_duplicates: bool = True) -> list[float]:
    """Parse a small, non-executable adaptive sweep expression.

    The accepted forms are ``values = [number, ...]``,
    ``values = linspace(start, stop, count)``, and
    ``values = logspace(start, stop, count)``.  Python statements, attribute
    access, imports, comprehensions, and arbitrary function calls are rejected.
    """
    code = (logic or "").strip()
    if not code:
        raise ValueError("Adaptive logic is empty. Define values = [...].")
    if len(code) > MAX_LOGIC_LENGTH:
        raise ValueError("Adaptive logic is too long.")
    values = _evaluate_values_expression(_parse_values_expression(code))
    if remove_duplicates:
        values = dedupe_adjacent_values(values)
    if not values:
        raise ValueError("Adaptive logic produced no values.")
    if len(values) > MAX_ADAPTIVE_POINTS:
        raise ValueError("Adaptive logic produced too many values for alpha UI.")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Adaptive logic produced NaN or infinite source values.")
    return values


DEFAULT_ADAPTIVE_LOGIC = logic_from_rule(default_log_rule())
