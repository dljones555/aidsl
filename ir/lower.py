"""Lowering: Layer 1 DSL (.ai Program AST) -> Layer 2 IR (Spec).

The lowering table — every DSL construct gets its IR fate:

  DEFINE <schema>      -> type
  FROM <source>        -> knowledge entry (fs://...); the binding resolves it
  EXTRACT <schema>     -> op effect external, cap model.complete, using prompt
  CLASSIFY ...         -> op effect external, cap model.complete, using prompt
  DRAFT ...            -> op effect external, cap model.complete, using prompt
  FLAG WHEN <cond>     -> audit rule (standing deterministic policy, action flag)
  OUTPUT <file>        -> op effect recorded (the receipt sink)
  SET ...              -> DROPPED: model/temperature/seed are binding
                          configuration. Changing the model must not change
                          the durable definition. ("The header is the
                          contract" — the model is not in the header.)
  PROMPT / EXAMPLES    -> attached to the op as using prompt "<name>"

Plan "main" threads the ops: extract -> classify -> draft -> output,
each feeding the next. This is v0.1: one plan, linear flow.
"""

from __future__ import annotations

from aidsl.parser import Condition, Program

from .model import (
    AuditRule,
    Effect,
    Field,
    Knowledge,
    Op,
    Plan,
    PlanStep,
    Spec,
    TypeDef,
)

_DSL_TYPE_MAP = {
    "TEXT": "text",
    "MONEY": "money",
    "NUMBER": "number",
    "YES/NO": "bool",
    "BOOL": "bool",
    "DATETIME": "date",
}


def _field_type(ftype: str, enum_values: list[str], ref_type: str) -> str:
    if ftype == "ENUM":
        return f"enum[{', '.join(enum_values)}]"
    if ftype == "LIST":
        inner = _DSL_TYPE_MAP.get(ref_type, ref_type.lower() or "text")
        return f"{inner}[]"
    if ftype == "REF":
        return ref_type.lower() or "text"
    return _DSL_TYPE_MAP.get(ftype, "text")


def _cond_to_expr(cond: Condition) -> str:
    op = {"OVER": ">", "UNDER": "<", "IS": "=="}.get(cond.op, "==")
    value = cond.value.strip()
    low = value.lower()
    if low in ("true", "false"):
        value = low
    elif not value.replace(".", "", 1).replace("-", "", 1).isdigit():
        value = f'"{value}"'
    return f"{cond.field} {op} {value}"


def _flag_to_expr(conditions: list[Condition], conjunctions: list[str]) -> str:
    parts = [_cond_to_expr(c) for c in conditions]
    expr = parts[0]
    for conj, part in zip(conjunctions, parts[1:]):
        expr += f" {conj.lower()} {part}"
    return expr


def _lower_types(program: Program, spec: Spec) -> None:
    """DEFINE <schema> -> IR type. Portable declarations; the Layer 1
    compiler (aidsl/compiler.py) separately builds Pydantic models from
    these for runtime validation — the IR itself takes no Pydantic
    dependency, so the definition stays portable."""
    for sname, schema in program.schemas.items():
        tdef = TypeDef(name=sname.lower())
        for f in schema.fields:
            tdef.fields.append(
                Field(f.name, _field_type(f.type, f.enum_values, f.ref_type))
            )
        spec.types.append(tdef)


def _lower_source(program: Program, spec: Spec) -> None:
    """FROM <source> -> knowledge entry. fs:// names a file; the host
    binding reads it (jsonl = one JSON record per line, the stream
    convention for record lists)."""
    if program.source:
        target = (program.extract_target or "records").lower()
        spec.knowledge.append(
            Knowledge(name=f"{target}_source", uri=f"fs://{program.source}")
        )


def _lower_extract(
    program: Program, spec: Spec, target: str, prompt: str, steps: list[PlanStep]
) -> str:
    """EXTRACT -> external op calling the model. Returns the result var."""
    if not program.extract_target:
        return ""
    # "using" names the prompt; the host binding resolves the name to the
    # prompt text and where it lives. The IR never holds prompt bodies.
    op = Op(
        name=f"extract_{target}",
        params=["source"],
        returns=target,
        effect=Effect.EXTERNAL,
        capability="model.complete",
        using=prompt,
        using_kind="prompt",
    )
    spec.ops.append(op)
    steps.append(PlanStep(var="raw", op=op.name, args=[f"{target}_source"]))
    return "raw"


def _lower_classify(
    program: Program,
    spec: Spec,
    target: str,
    prompt: str,
    last_var: str,
    steps: list[PlanStep],
) -> str:
    """CLASSIFY -> external op. Returns the result var (unchanged if absent)."""
    if not program.classify:
        return last_var
    cfield = program.classify.field_name or "classification"
    op = Op(
        name=f"classify_{cfield}",
        params=[last_var or target],
        returns=target,
        effect=Effect.EXTERNAL,
        capability="model.complete",
        using=prompt,
        using_kind="prompt",
    )
    spec.ops.append(op)
    prev, last_var = last_var, "classified"
    steps.append(PlanStep(var=last_var, op=op.name, args=[prev]))
    return last_var


def _lower_draft(
    program: Program,
    spec: Spec,
    target: str,
    prompt: str,
    last_var: str,
    steps: list[PlanStep],
) -> str:
    """DRAFT -> external op, plus the draft record type. Returns the result var."""
    if not program.draft:
        return last_var
    dfield = program.draft.field_name or "draft"
    prompt_name = program.draft.prompt_name or prompt
    op = Op(
        name=f"draft_{dfield}",
        params=[last_var or target],
        returns="draft",
        effect=Effect.EXTERNAL,
        capability="model.complete",
        using=prompt_name,
        using_kind="prompt",
    )
    spec.ops.append(op)
    if not any(t.name == "draft" for t in spec.types):
        spec.types.append(
            TypeDef(
                "draft",
                [
                    Field("to", "text"),
                    Field("subject", "text"),
                    Field("body", "text"),
                ],
            )
        )
    prev, last_var = last_var, "drafted"
    steps.append(PlanStep(var=last_var, op=op.name, args=[prev]))
    return last_var


def _lower_flags(program: Program, spec: Spec) -> None:
    """FLAG WHEN -> standing audit rules (action flag). Deterministic policy."""
    for i, flag in enumerate(program.flags, 1):
        spec.audits.append(
            AuditRule(
                name=f"flag_{i}",
                expr=_flag_to_expr(flag.conditions, flag.conjunctions),
                action="flag",
            )
        )


def _lower_output(
    program: Program,
    spec: Spec,
    target: str,
    last_var: str,
    steps: list[PlanStep],
) -> None:
    """OUTPUT -> recorded op: the receipt sink (fs.write capability)."""
    if not program.output:
        return
    op = Op(
        name="write_output",
        params=[last_var or target],
        returns="receipt",
        effect=Effect.RECORDED,
        capability="fs.write",
    )
    spec.ops.append(op)
    steps.append(PlanStep(var="out", op=op.name, args=[last_var or target]))


def _lower_ops(program: Program, spec: Spec) -> list[PlanStep]:
    """Thread the verb ops into plan steps: extract -> classify -> draft -> output."""
    target = (program.extract_target or "record").lower()
    prompt = program.prompt_name or "default"
    steps: list[PlanStep] = []
    last_var = _lower_extract(program, spec, target, prompt, steps)
    last_var = _lower_classify(program, spec, target, prompt, last_var, steps)
    last_var = _lower_draft(program, spec, target, prompt, last_var, steps)
    _lower_flags(program, spec)
    _lower_output(program, spec, target, last_var, steps)
    return steps


def lower_program(program: Program, name: str = "spec", version: str = "v1") -> Spec:
    """Lower an aidsl Program AST to an IR Spec."""
    spec = Spec(name=name, version=version)
    _lower_types(program, spec)
    _lower_source(program, spec)
    steps = _lower_ops(program, spec)
    if steps:
        spec.plans.append(Plan(name="main", steps=steps))

    # SET is binding config — deliberately absent from the IR.
    return spec
