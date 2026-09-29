"""Tiny safe expression evaluator for IR `when` clauses and audit predicates.

Supports: names, attribute access (a.b.c), constants, comparisons
(==, !=, <, <=, >, >=), boolean and/or/not, and + - * / on numbers.
Anything else raises. Never uses eval().
"""

from __future__ import annotations

import ast
import operator

_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _resolve(node: ast.AST, env: dict) -> object:
    if isinstance(node, ast.Expression):
        return _resolve(node.body, env)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id == "true":
            return True
        if node.id == "false":
            return False
        if node.id not in env:
            raise NameError(f"unknown name: {node.id}")
        return env[node.id]
    if isinstance(node, ast.Attribute):
        obj = _resolve(node.value, env)
        if isinstance(obj, dict):
            if node.attr not in obj:
                raise NameError(f"unknown field: {node.attr}")
            return obj[node.attr]
        return getattr(obj, node.attr)
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            result: object = True
            for v in node.values:
                result = _resolve(v, env)
                if not result:
                    return False
            return result
        if isinstance(node.op, ast.Or):
            for v in node.values:
                result = _resolve(v, env)
                if result:
                    return True
            return False
        raise ValueError("unsupported boolean operator")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _resolve(node.operand, env)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_resolve(node.operand, env)  # type: ignore[operator]
    if isinstance(node, ast.Compare):
        left = _resolve(node.left, env)
        for op, comp in zip(node.ops, node.comparators):
            fn = _OPS.get(type(op))
            if fn is None:
                raise ValueError(f"unsupported comparison: {type(op).__name__}")
            right = _resolve(comp, env)
            if not fn(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.BinOp):
        fn = _OPS.get(type(node.op))
        if fn is None:
            raise ValueError(f"unsupported operator: {type(node.op).__name__}")
        return fn(_resolve(node.left, env), _resolve(node.right, env))
    raise ValueError(f"unsupported expression: {ast.dump(node)}")


def parse_ok(expr: str) -> bool:
    """True if the expression parses (used by the checker)."""
    try:
        _resolve(ast.parse(expr, mode="eval"), {})
        return True
    except (NameError, AttributeError):
        # Names resolve at run time; parse-level only cares about syntax.
        return True
    except (SyntaxError, ValueError, TypeError):
        return False


def evaluate(expr: str, env: dict) -> object:
    """Evaluate a boolean/value expression against env. Raises on any problem."""
    if not expr.strip():
        return True
    tree = ast.parse(expr, mode="eval")
    return _resolve(tree, env)
