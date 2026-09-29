"""Checker: right-sized verification for IR specs.

Deterministic, no model calls. A spec that fails check() should not run.
Each violation carries a code so the designer surface can explain it.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import eval as ir_eval
from .model import AUDIT_ACTIONS, BUILTIN_TYPES, Effect, Spec


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


def check(spec: Spec) -> list[Violation]:
    v: list[Violation] = []
    op_names = [o.name for o in spec.ops]
    gate_names = [g.name for g in spec.gates]
    type_names = {t.name for t in spec.types} | BUILTIN_TYPES | {"enum"}

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
            if step.when and not ir_eval.parse_ok(step.when):
                v.append(
                    Violation(
                        "IR-09",
                        f"plan '{plan.name}' step '{step.var}' has "
                        f"unparsable when-clause: {step.when!r}",
                    )
                )

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

    for audit in spec.audits:
        if audit.action not in AUDIT_ACTIONS:
            v.append(
                Violation(
                    "IR-06",
                    f"audit '{audit.name}' has unknown action "
                    f"'{audit.action}' (want one of {sorted(AUDIT_ACTIONS)})",
                )
            )
        if not ir_eval.parse_ok(audit.expr):
            v.append(
                Violation(
                    "IR-07",
                    f"audit '{audit.name}' has unparsable expression: {audit.expr!r}",
                )
            )

    return v
