"""Predicate evaluator: the tiny safe expression engine for IR `when` clauses.

Supports: names, attribute access (a.b.c), constants, comparisons
(==, !=, <, <=, >, >=), boolean and/or/not, and + - * / on numbers.
Anything else raises. Never uses eval() — the AST is walked, not executed.

Named "evaluator" (not "eval") because in the AI age "eval" means
model-output evaluation. This is expression evaluation: the predicate
layer that `when` clauses and audit rules run on.
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


def _resolve_name(node: ast.Name, env: dict) -> object:
    if node.id == "true":
        return True
    if node.id == "false":
        return False
    if node.id not in env:
        raise NameError(f"unknown name: {node.id}")
    return env[node.id]


def _resolve_attr(node: ast.Attribute, env: dict) -> object:
    obj = _resolve(node.value, env)
    if isinstance(obj, dict):
        if node.attr not in obj:
            raise NameError(f"unknown field: {node.attr}")
        return obj[node.attr]
    return getattr(obj, node.attr)


def _resolve_boolop(node: ast.BoolOp, env: dict) -> object:
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


def _resolve_unary(node: ast.UnaryOp, env: dict) -> object:
    if isinstance(node.op, ast.Not):
        return not _resolve(node.operand, env)
    if isinstance(node.op, ast.USub):
        return -_resolve(node.operand, env)  # type: ignore[operator]
    raise ValueError(f"unsupported expression: {ast.dump(node)}")


def _resolve_compare(node: ast.Compare, env: dict) -> object:
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


def _resolve_binop(node: ast.BinOp, env: dict) -> object:
    fn = _OPS.get(type(node.op))
    if fn is None:
        raise ValueError(f"unsupported operator: {type(node.op).__name__}")
    return fn(_resolve(node.left, env), _resolve(node.right, env))


def _resolve(node: ast.AST, env: dict) -> object:
    """Resolve one AST node against env. Dispatches by node type."""
    match node:
        case ast.Expression():
            return _resolve(node.body, env)
        case ast.Constant():
            return node.value
        case ast.Name():
            return _resolve_name(node, env)
        case ast.Attribute():
            return _resolve_attr(node, env)
        case ast.BoolOp():
            return _resolve_boolop(node, env)
        case ast.UnaryOp():
            return _resolve_unary(node, env)
        case ast.Compare():
            return _resolve_compare(node, env)
        case ast.BinOp():
            return _resolve_binop(node, env)
        case _:
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
