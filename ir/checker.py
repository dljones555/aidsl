"""Checker: right-sized verification for IR specs.

Deterministic, no model calls. A spec that fails check() should not run.
Each violation carries a code so the designer surface can explain it.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import evaluator as ir_evaluator
from .model import AUDIT_ACTIONS, BUILTIN_TYPES, Effect, Plan, Spec


@dataclass
class Violation:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def _base_type(t: str) -> str:
    t = t.strip()
    t = t.removesuffix("[]")
    if t.startswith("enum["):
        return "enum"
    return t


def _check_plan_refs(spec: Spec, v: list[Violation]) -> None:
    """Steps must call defined ops; when-clauses must parse. (IR-01, IR-08, IR-09)"""
    op_names = [o.name for o in spec.ops]
    for name in set(op_names):
        if op_names.count(name) > 1:
            v.append(Violation("IR-08", f"duplicate op name: {name}"))
    for plan in spec.plans:
        for step in plan.steps:
            if step.op not in op_names:
                v.append(
                    Violation(
                        "IR-01",
                        f"plan '{plan.name}' step '{step.var}' calls "
                        f"undefined op '{step.op}'",
                    )
                )
            if step.when and not ir_evaluator.parse_ok(step.when):
                v.append(
                    Violation(
                        "IR-09",
                        f"plan '{plan.name}' step '{step.var}' has "
                        f"unparsable when-clause: {step.when!r}",
                    )
                )


def _check_op_contracts(spec: Spec, v: list[Violation]) -> None:
    """Gates must exist, return types must be declared, external ops need a
    gate or a deny list, and pure ops must not declare prompts. (IR-02..IR-05)"""
    gate_names = [g.name for g in spec.gates]
    type_names = {t.name for t in spec.types} | BUILTIN_TYPES | {"enum"}
    for op in spec.ops:
        if op.gate and op.gate not in gate_names:
            v.append(
                Violation(
                    "IR-02", f"op '{op.name}' references undefined gate '{op.gate}'"
                )
            )
        if _base_type(op.returns) not in type_names:
            v.append(
                Violation(
                    "IR-03",
                    f"op '{op.name}' returns undefined type '{op.returns}'",
                )
            )
        if op.effect == Effect.EXTERNAL and not op.gate and not spec.deny:
            v.append(
                Violation(
                    "IR-04",
                    f"external op '{op.name}' has no gate and the spec "
                    f"declares no deny list — it could act unconstrained. "
                    f"Add a gate or a deny entry (shadow mode).",
                )
            )
        if op.effect == Effect.PURE and op.using_kind == "prompt":
            v.append(
                Violation(
                    "IR-05",
                    f"pure op '{op.name}' declares a prompt — prompts imply "
                    f"model calls. Mark it external (with a gate), or make it "
                    f"deterministic.",
                )
            )


def _check_audits(spec: Spec, v: list[Violation]) -> None:
    """Audit rules need known actions and parsable expressions. (IR-06, IR-07)"""
    for audit in spec.audits:
        if audit.action not in AUDIT_ACTIONS:
            v.append(
                Violation(
                    "IR-06",
                    f"audit '{audit.name}' has unknown action "
                    f"'{audit.action}' (want one of {sorted(AUDIT_ACTIONS)})",
                )
            )
        if not ir_evaluator.parse_ok(audit.expr):
            v.append(
                Violation(
                    "IR-07",
                    f"audit '{audit.name}' has unparsable expression: {audit.expr!r}",
                )
            )


def _find_cycle(plan: Plan) -> list[str]:
    """One dependency cycle as a var path (a -> b -> a), or [] if acyclic."""
    known = {s.var for s in plan.steps}
    deps = {s.var: [d for d in s.depends_on if d in known] for s in plan.steps}
    visiting: list[str] = []  # the current DFS path
    visited: set[str] = set()

    def visit(var: str) -> list[str]:
        if var in visiting:
            return visiting[visiting.index(var) :] + [var]
        if var in visited:
            return []
        visiting.append(var)
        for dep in deps[var]:
            hit = visit(dep)
            if hit:
                return hit
        visiting.pop()
        visited.add(var)
        return []

    for step in plan.steps:
        hit = visit(step.var)
        if hit:
            return hit
    return []


def _check_plan_dependencies(spec: Spec, v: list[Violation]) -> None:
    """depends_on must name steps in the same plan, and the graph must be
    acyclic — otherwise no execution order exists. (IR-10, IR-11)"""
    for plan in spec.plans:
        step_vars = {s.var for s in plan.steps}
        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in step_vars:
                    v.append(
                        Violation(
                            "IR-10",
                            f"plan '{plan.name}' step '{step.var}' depends on "
                            f"unknown step '{dep}'",
                        )
                    )
        cycle = _find_cycle(plan)
        if cycle:
            v.append(
                Violation(
                    "IR-11",
                    f"plan '{plan.name}' has a dependency cycle: {' -> '.join(cycle)}",
                )
            )


def check(spec: Spec) -> list[Violation]:
    """Check a spec. Returns violations; an empty list means runnable."""
    v: list[Violation] = []
    _check_plan_refs(spec, v)
    _check_plan_dependencies(spec, v)
    _check_op_contracts(spec, v)
    _check_audits(spec, v)
    return v
