"""Work Surface IR — Layer 2, the durable contract.

Everything is a type, op, plan, gate, or audit rule. Each op is
effect-typed: pure / recorded / external / suspend — the human-CPU-GPU
triad as effect classes with different latency/cost profiles.

The DSL (Layer 1, the .ai authoring skin) compiles *down* to this.
This module is the model plus the canonical text form: ``dumps`` prints
it, ``loads`` reads it back. The printed form is the customer-owned
artifact — "you get a folder, it's yours."

v0.1 first cut. Deliberately small; see lower.py for the DSL mapping.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Effect(str, Enum):
    PURE = "pure"  # deterministic, no side effects, free (CPU lane)
    RECORDED = "recorded"  # deterministic, emits evidence (CPU lane + receipt)
    EXTERNAL = "external"  # calls out: model, API, action (GPU lane)
    SUSPEND = "suspend"  # pauses for a human gate (human lane)


BUILTIN_TYPES = {"text", "number", "float", "int", "bool", "money", "date", "receipt"}

AUDIT_ACTIONS = {"flag", "deny", "suspend"}


@dataclass
class Field:
    name: str
    type: str  # text | number | money | bool | date | enum[a, b] | Type | Type[]


@dataclass
class TypeDef:
    name: str
    fields: list[Field] = field(default_factory=list)


@dataclass
class Op:
    name: str
    params: list[str] = field(default_factory=list)
    returns: str = "receipt"
    effect: Effect = Effect.PURE
    capability: str = ""  # e.g. model.complete, action.execute — what deny: matches
    using: str = ""  # prompt name or deterministic rule name
    using_kind: str = ""  # "prompt" | "deterministic" | ""
    gate: str = ""  # gate name, required before an external op runs


@dataclass
class Gate:
    name: str
    verdicts: list[str] = field(default_factory=list)  # the recorded verdict vocabulary


@dataclass
class AuditRule:
    name: str
    expr: str = ""  # boolean expression over metrics or record fields
    action: str = "flag"  # flag | deny | suspend


@dataclass
class PlanStep:
    var: str
    op: str
    args: list[str] = field(default_factory=list)
    when: str = ""  # boolean expression; empty means always


@dataclass
class Plan:
    name: str
    steps: list[PlanStep] = field(default_factory=list)


@dataclass
class Knowledge:
    name: str
    uri: str  # kv://..., fs://... — the binding resolves it, the IR just names it


@dataclass
class Spec:
    name: str
    version: str = "v1"
    parent: str = "none"
    author: str = ""
    goal: str = ""
    budget_tokens: int = 0
    budget_human_minutes: int = 0
    knowledge: list[Knowledge] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)  # declared capabilities
    deny: list[str] = field(default_factory=list)  # denied capabilities (shadow mode)
    types: list[TypeDef] = field(default_factory=list)
    ops: list[Op] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)
    audits: list[AuditRule] = field(default_factory=list)
    plans: list[Plan] = field(default_factory=list)

    def op_map(self) -> dict[str, Op]:
        return {o.name: o for o in self.ops}

    def gate_map(self) -> dict[str, Gate]:
        return {g.name: g for g in self.gates}

    def type_map(self) -> dict[str, TypeDef]:
        return {t.name: t for t in self.types}


# ---------------------------------------------------------------------------
# Canonical text form
# ---------------------------------------------------------------------------


def _q(s: str) -> str:
    return '"' + s.replace('"', '\\"') + '"'


def dumps(spec: Spec) -> str:
    """Print the spec in canonical form. Deterministic: same spec, same text."""
    out: list[str] = []
    out.append(f"spec {spec.name}@{spec.version}")
    out.append(f"  parent {spec.parent}")
    if spec.author:
        out.append(f"  author {_q(spec.author)}")
    if spec.goal:
        out.append(f"  goal {_q(spec.goal)}")
    if spec.budget_tokens or spec.budget_human_minutes:
        out.append(
            f"  budget tokens {spec.budget_tokens}"
            f" human_minutes {spec.budget_human_minutes}"
        )
    out.append("")
    if spec.knowledge:
        out.append("knowledge:")
        for k in spec.knowledge:
            out.append(f"  {k.name} @ {_q(k.uri)}")
        out.append("")
    if spec.effects:
        out.append(f"effects: {', '.join(spec.effects)}")
    if spec.deny:
        out.append(f"deny: {', '.join(spec.deny)}")
    if spec.effects or spec.deny:
        out.append("")
    for t in spec.types:
        fields = ", ".join(f"{fl.name}: {fl.type}" for fl in t.fields)
        out.append(f"type {t.name} = {{ {fields} }}")
    if spec.types:
        out.append("")
    for o in spec.ops:
        params = ", ".join(o.params)
        line = f"op {o.name}({params}) -> {o.returns} effect {o.effect.value}"
        if o.capability:
            line += f" cap {o.capability}"
        if o.using:
            line += f" using {o.using_kind} {_q(o.using)}"
        if o.gate:
            line += f" gate {o.gate}"
        out.append(line)
    if spec.ops:
        out.append("")
    for g in spec.gates:
        out.append(f"gate {g.name}:")
        out.append(f"  human decides in [{', '.join(g.verdicts)}]")
        out.append("")
    for a in spec.audits:
        out.append(f"audit {a.name}: {a.expr} -> {a.action}")
    if spec.audits:
        out.append("")
    for p in spec.plans:
        out.append(f"plan {p.name}:")
        for s in p.steps:
            args = ", ".join(s.args)
            line = f"  {s.var} = {s.op}({args})"
            if s.when:
                line += f" when {s.when}"
            out.append(line)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def _split_top_commas(s: str) -> list[str]:
    """Split on commas that are not inside [...] (for enum[...] field types)."""
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def _unq(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1].replace('\\"', '"')
    return s


def loads(text: str) -> Spec:
    """Read the canonical form back. Round-trips with dumps()."""
    spec: Spec | None = None
    section: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not raw.startswith((" ", "\t")):
            section = None
            m = re.match(r"spec\s+(\w+)@(\S+)", line)
            if m:
                spec = Spec(name=m.group(1), version=m.group(2))
                continue
            if line == "knowledge:":
                section = "knowledge"
                continue
            m = re.match(r"effects:\s*(.*)", line)
            if m:
                assert spec is not None
                spec.effects = [e.strip() for e in m.group(1).split(",") if e.strip()]
                continue
            m = re.match(r"deny:\s*(.*)", line)
            if m:
                assert spec is not None
                spec.deny = [d.strip() for d in m.group(1).split(",") if d.strip()]
                continue
            m = re.match(r"type\s+(\w+)\s*=\s*\{(.*)\}", line)
            if m:
                assert spec is not None
                fields = []
                for part in _split_top_commas(m.group(2)):
                    fname, _, ftype = part.partition(":")
                    fields.append(Field(fname.strip(), ftype.strip()))
                spec.types.append(TypeDef(m.group(1), fields))
                continue
            m = re.match(
                r"op\s+(\w+)\(([^)]*)\)\s*->\s*(\S+)\s+effect\s+(\w+)(.*)", line
            )
            if m:
                assert spec is not None
                name, params, returns, effect, rest = m.groups()
                op = Op(
                    name=name,
                    params=[p.strip() for p in params.split(",") if p.strip()],
                    returns=returns,
                    effect=Effect(effect),
                )
                m2 = re.search(r"cap\s+(\S+)", rest)
                if m2:
                    op.capability = m2.group(1)
                m2 = re.search(
                    r'using\s+(prompt|deterministic)\s+"((?:[^"\\]|\\.)*)"', rest
                )
                if m2:
                    op.using_kind, op.using = m2.group(1), _unq('"' + m2.group(2) + '"')
                m2 = re.search(r"gate\s+(\w+)", rest)
                if m2:
                    op.gate = m2.group(1)
                spec.ops.append(op)
                continue
            m = re.match(r"gate\s+(\w+):", line)
            if m:
                assert spec is not None
                spec.gates.append(Gate(m.group(1)))
                section = "gate"
                continue
            m = re.match(r"audit\s+(\w+):\s*(.+?)\s*->\s*(\w+)", line)
            if m:
                assert spec is not None
                spec.audits.append(
                    AuditRule(name=m.group(1), expr=m.group(2), action=m.group(3))
                )
                continue
            m = re.match(r"plan\s+(\w+):", line)
            if m:
                assert spec is not None
                spec.plans.append(Plan(m.group(1)))
                section = "plan"
                continue
            raise ValueError(f"IR parse error: {line!r}")
        else:
            assert spec is not None
            s = line.strip()
            if section == "knowledge":
                m = re.match(r"(\w+)\s+@\s+(\".*\")", s)
                if m:
                    spec.knowledge.append(Knowledge(m.group(1), _unq(m.group(2))))
            elif s.startswith("parent "):
                spec.parent = s[len("parent ") :].strip()
            elif s.startswith("author "):
                spec.author = _unq(s[len("author ") :])
            elif s.startswith("goal "):
                spec.goal = _unq(s[len("goal ") :])
            elif s.startswith("budget "):
                m = re.search(r"tokens\s+(\d+)", s)
                if m:
                    spec.budget_tokens = int(m.group(1))
                m = re.search(r"human_minutes\s+(\d+)", s)
                if m:
                    spec.budget_human_minutes = int(m.group(1))
            elif section == "gate" and s.startswith("human decides in "):
                m = re.search(r"\[(.*)\]", s)
                if m and spec.gates:
                    spec.gates[-1].verdicts = [
                        v.strip() for v in m.group(1).split(",") if v.strip()
                    ]
            elif section == "plan":
                m = re.match(r"(\w+)\s*=\s*(\w+)\(([^)]*)\)(?:\s+when\s+(.+))?", s)
                if not m:
                    raise ValueError(f"IR parse error in plan step: {s!r}")
                var, op, args, when = m.groups()
                spec.plans[-1].steps.append(
                    PlanStep(
                        var=var,
                        op=op,
                        args=[a.strip() for a in args.split(",") if a.strip()],
                        when=(when or "").strip(),
                    )
                )
            else:
                raise ValueError(f"IR parse error: {s!r}")
    if spec is None:
        raise ValueError("IR parse error: no spec header")
    return spec
