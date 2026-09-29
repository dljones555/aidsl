"""Executor: runs an IR plan. This is the part David named.

It executes the contract; models (and humans) are temp workers it hires.
Deterministic: same spec + same model responses + same verdicts = same
receipt. The receipt is the verifiable artifact of a run.

v0.1 semantics:
  - pure / recorded ops run via op_impls (caller-supplied callables).
  - external ops call the ModelClient — unless denied. Deny matches the
    op name or its capability. A denied external op with no gate stops the
    run (status "denied"). A denied external op WITH a gate still asks the
    human; an approving verdict records "shadow_blocked" and the run
    continues — the send exists in the spec but cannot run yet.
  - gates suspend the run until a verdict arrives (the human lane).
  - a step whose arg is a list fans out over elements; a `when` clause on
    a fanned step filters elements.
  - budget audits (action suspend/deny) are evaluated after the run.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from . import eval as ir_eval
from .model import Effect, Op, Spec
from .stub import GateIO, ModelClient, ModelResult

PROCEED_VERDICTS = {"approve", "advance"}
HUMAN_MINUTES_PER_VERDICT = 5


@dataclass
class StepReceipt:
    var: str
    op: str
    effect: str
    inputs_digest: str
    outputs_digest: str
    tokens_in: int = 0
    tokens_out: int = 0
    flags: list[str] = field(default_factory=list)
    gate: str = ""
    verdict: str = ""
    skipped: bool = False
    suspended: bool = False
    shadow_blocked: bool = False
    dropped: bool = False


@dataclass
class RunReceipt:
    spec: str
    version: str
    plan: str
    steps: list[StepReceipt] = field(default_factory=list)
    tokens_used: int = 0
    human_minutes_used: int = 0
    audit_failures: list[str] = field(default_factory=list)
    status: str = "completed"  # completed | suspended | denied

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec": self.spec,
            "version": self.version,
            "plan": self.plan,
            "status": self.status,
            "tokens_used": self.tokens_used,
            "human_minutes_used": self.human_minutes_used,
            "audit_failures": self.audit_failures,
            "steps": [
                {
                    "var": s.var,
                    "op": s.op,
                    "effect": s.effect,
                    "inputs": s.inputs_digest,
                    "outputs": s.outputs_digest,
                    "tokens_in": s.tokens_in,
                    "tokens_out": s.tokens_out,
                    "flags": s.flags,
                    "gate": s.gate,
                    "verdict": s.verdict,
                    "skipped": s.skipped,
                    "suspended": s.suspended,
                    "shadow_blocked": s.shadow_blocked,
                    "dropped": s.dropped,
                }
                for s in self.steps
            ],
        }


class _Dropped:
    """Sentinel: the item was dropped by a gate verdict (reject/hold)."""


class _Suspended(Exception):
    pass


class _Denied(Exception):
    pass


def _digest(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def prompt_for_op(op: Op, inputs: Any) -> str:
    return (
        f"op {op.name} ({op.using_kind or 'no-using'}: {op.using or 'n/a'})\n"
        f"effect {op.effect.value}\n"
        f"input: {json.dumps(inputs, default=str)[:2000]}"
    )


def _flag_audits(spec: Spec, record: Any) -> list[str]:
    fired: list[str] = []
    env = record if isinstance(record, dict) else {"value": record}
    for audit in spec.audits:
        if audit.action != "flag":
            continue
        try:
            fired_now = bool(ir_eval.evaluate(audit.expr, dict(env)))
        except Exception:  # noqa: BLE001 - a broken audit must not crash a run
            fired_now = False
        if fired_now:
            fired.append(audit.name)
    return fired


class Executor:
    def __init__(
        self,
        spec: Spec,
        model: ModelClient,
        op_impls: dict[str, Callable[..., Any]] | None = None,
        gate_io: GateIO | None = None,
    ):
        self.spec = spec
        self.model = model
        self.op_impls = op_impls or {}
        self.gate_io = gate_io
        self.ops = spec.op_map()
        self.gates = spec.gate_map()

    def _denied(self, op: Op) -> bool:
        return any(d == op.name or d == op.capability for d in self.spec.deny)

    def run(self, plan_name: str = "") -> RunReceipt:
        plan = next(
            (p for p in self.spec.plans if not plan_name or p.name == plan_name), None
        )
        if plan is None:
            raise ValueError(f"no plan {plan_name!r} in spec {self.spec.name}")
        receipt = RunReceipt(
            spec=self.spec.name, version=self.spec.version, plan=plan.name
        )
        env: dict[str, Any] = {}

        for step in plan.steps:
            op = self.ops.get(step.op)
            if op is None:
                raise ValueError(f"undefined op '{step.op}'")
            args = [env[a] for a in step.args]
            sr = StepReceipt(
                var=step.var,
                op=op.name,
                effect=op.effect.value,
                inputs_digest=_digest(args),
                outputs_digest="",
            )
            try:
                if len(args) == 1 and isinstance(args[0], list):
                    items = args[0]
                    if step.when:
                        items = [
                            it
                            for it in items
                            if ir_eval.evaluate(step.when, {step.args[0]: it})
                        ]
                    outputs = [self._call(op, it, sr) for it in items]
                    outputs = [o for o in outputs if not isinstance(o, _Dropped)]
                    env[step.var] = outputs
                else:
                    if step.when and not ir_eval.evaluate(
                        step.when, dict(zip(step.args, args))
                    ):
                        sr.skipped = True
                        env[step.var] = None
                    else:
                        arg = args[0] if len(args) == 1 else args
                        out = self._call(op, arg, sr)
                        if isinstance(out, _Dropped):
                            sr.dropped = True
                            env[step.var] = None
                        else:
                            env[step.var] = out
                sr.outputs_digest = _digest(env[step.var])
            except _Suspended:
                receipt.steps.append(sr)
                receipt.status = "suspended"
                break
            except _Denied:
                receipt.steps.append(sr)
                receipt.status = "denied"
                break

            receipt.tokens_used += sr.tokens_in + sr.tokens_out
            receipt.steps.append(sr)

        receipt.human_minutes_used = HUMAN_MINUTES_PER_VERDICT * sum(
            1 for s in receipt.steps if s.verdict
        )
        metrics = {
            "tokens_used": receipt.tokens_used,
            "human_minutes_used": receipt.human_minutes_used,
            "cost_usd": 0,
        }
        for audit in self.spec.audits:
            if audit.action in ("suspend", "deny"):
                try:
                    if not ir_eval.evaluate(audit.expr, metrics):
                        receipt.audit_failures.append(audit.name)
                except Exception as e:  # noqa: BLE001 - eval failure IS an audit failure
                    receipt.audit_failures.append(f"{audit.name} (eval error: {e})")
        return receipt

    def _call(self, op: Op, inputs: Any, sr: StepReceipt) -> Any:
        if op.effect in (Effect.PURE, Effect.RECORDED):
            fn = self.op_impls.get(op.name)
            if fn is None:
                raise ValueError(f"no implementation for op '{op.name}'")
            return fn(inputs)

        if op.effect == Effect.EXTERNAL:
            if self._denied(op) and not op.gate:
                raise _Denied(f"op '{op.name}' denied by spec deny list")

            if op.gate:
                gate = self.gates[op.gate]
                verdict = ""
                if self.gate_io is not None:
                    verdict = self.gate_io.ask_verdict(gate, inputs) or ""
                sr.gate = gate.name
                sr.verdict = verdict
                if not verdict:
                    sr.suspended = True
                    raise _Suspended(f"gate '{gate.name}' awaiting verdict")
                if verdict not in PROCEED_VERDICTS:
                    return _Dropped()

            if self._denied(op):
                # Human approved, but shadow mode: the send exists in the
                # spec but cannot run yet.
                sr.shadow_blocked = True
                return None

            result: ModelResult = self.model.complete(
                op=op.name,
                prompt=prompt_for_op(op, inputs),
                schema={"returns": op.returns},
            )
            sr.tokens_in += result.tokens_in
            sr.tokens_out += result.tokens_out
            data = result.data
            records = data if isinstance(data, list) else [data]
            for rec in records:
                for f in _flag_audits(self.spec, rec):
                    if f not in sr.flags:
                        sr.flags.append(f)
            return data

        if op.effect == Effect.SUSPEND:
            raise _Suspended(f"op '{op.name}' suspends")

        raise ValueError(f"unknown effect {op.effect}")
