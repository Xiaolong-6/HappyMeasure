"""Restricted NumPy expression evaluator for custom map transforms."""

from __future__ import annotations

import ast
from collections.abc import Callable

import numpy as np

_FUNCTIONS: dict[str, Callable[..., np.ndarray | float]] = {
    "abs": np.abs,
    "sqrt": np.sqrt,
    "log": np.log,
    "log10": np.log10,
    "exp": np.exp,
    "clip": np.clip,
    "minimum": np.minimum,
    "maximum": np.maximum,
}


class ExpressionError(ValueError):
    """Raised when a custom expression is not in the safe expression subset."""


def evaluate_expression(expression: str, x: np.ndarray) -> np.ndarray:
    """Evaluate a small mathematical expression without Python execution."""

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"Invalid custom expression: {exc.msg}.") from exc

    def evaluate(node: ast.AST) -> np.ndarray | float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Name):
            if node.id == "x":
                return x
            raise ExpressionError(
                f"Unknown name {node.id!r}; only x and approved functions are allowed."
            )
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if isinstance(node.value, bool) or not np.isfinite(float(node.value)):
                raise ExpressionError("Numeric constants must be finite real numbers.")
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return +value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
        ):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            return left**right
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            function = _FUNCTIONS.get(node.func.id)
            if function is None:
                raise ExpressionError(f"Function {node.func.id!r} is not allowed.")
            if node.keywords:
                raise ExpressionError("Keyword arguments are not allowed in custom expressions.")
            return function(*(evaluate(argument) for argument in node.args))
        raise ExpressionError("Custom expression contains an unsupported operation.")

    try:
        with np.errstate(all="ignore"):
            result = evaluate(tree)
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise ExpressionError(f"Custom expression could not be evaluated: {exc}.") from exc
    return np.asarray(result, dtype=float)
