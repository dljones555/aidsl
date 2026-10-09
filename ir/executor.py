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
  - steps run in topological order of their depends_on DAG (listed order
    when no dependencies are declared).
  - budget audits (action suspend/deny) are evaluated after the run.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import evaluator as ir_evaluator
from .model import Effect, Op, Plan, PlanStep, Spec
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
    skip_reason: str = ""  # why skipped: "when condition false" or cascade
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
                    "skip_reason": s.skip_reason,
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
            fired_now = bool(ir_evaluator.evaluate(audit.expr, dict(env)))
        except Exception:  # noqa: BLE001 - a broken audit must not crash a run
            fired_now = False
        if fired_now:
            fired.append(audit.name)
    return fired


def _topo_order(plan: Plan) -> list[PlanStep]:
    """Order plan steps so each runs after its depends_on dependencies.

    Stable: unconstrained steps keep their listed order, so a plan with no
    depends_on runs exactly as listed. Unknown references and cycles are
    rejected by check() first; this raises loudly instead of hanging or
    silently misordering if they ever reach the executor.
    """
    by_var = {s.var: s for s in plan.steps}
    for step in plan.steps:
        for dep in step.depends_on:
            if dep not in by_var:
                raise ValueError(
                    f"plan '{plan.name}' step '{step.var}' depends on "
                    f"unknown step '{dep}'"
                )
    deps = {s.var: set(s.depends_on) for s in plan.steps}
    done: set[str] = set()
    ordered: list[PlanStep] = []
    while len(ordered) < len(plan.steps):
        progressed = False
        for step in plan.steps:  # listed order: the stability guarantee
            if step.var not in done and deps[step.var] <= done:
                ordered.append(step)
                done.add(step.var)
                progressed = True
        if not progressed:
            stuck = [s.var for s in plan.steps if s.var not in done]
            raise ValueError(
                f"plan '{plan.name}' has a dependency cycle involving: "
                + ", ".join(stuck)
            )
    return ordered


def _resolve_knowledge(uri: str) -> Any:
    """Resolve a knowledge URI to its value, seeding the run env.

    This is the piece _lower_source always promised ("the host binding
    reads it") but the reference executor never implemented: a plan step
    may name a knowledge entry as an argument (e.g. the extract step's
    "<target>_source"), and the entry must resolve before the first step
    runs. fs:// URIs are JSONL: one record per line. Paths resolve
    against the current working directory.
    """
    if uri.startswith("fs://"):
        path = uri[len("fs://") :]
        return [
            json.loads(line)
            for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    raise ValueError(f"unsupported knowledge uri: {uri!r}")


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

    def _find_plan(self, plan_name: str) -> Plan:
        """Locate the plan to run; an empty name means the first plan."""
        plan = next(
            (p for p in self.spec.plans if not plan_name or p.name == plan_name), None
        )
        if plan is None:
            raise ValueError(f"no plan {plan_name!r} in spec {self.spec.name}")
        return plan

    def run(self, plan_name: str = "") -> RunReceipt:
        """Run a plan. Suspends on human gates, stops on deny, else completes."""
        plan = self._find_plan(plan_name)
        receipt = RunReceipt(
            spec=self.spec.name, version=self.spec.version, plan=plan.name
        )
        env: dict[str, Any] = {}

        # Knowledge seeds the env: a step may take a knowledge entry as an
        # argument (the .ai lowering names it "<target>_source"), and it
        # must resolve before the first step runs.
        for k in self.spec.knowledge:
            if k.name not in env:
                env[k.name] = _resolve_knowledge(k.uri)

        # The reference executor stays sequential, but it follows the
        # depends_on DAG rather than listed order. Steps with no shared
        # dependencies are parallelizable by DAG-capable backends —
        # ordering and concurrency permission derive from this same
        # declaration; each backend owns its own scheduling.
        skipped: set[str] = set()  # vars whose steps produced no output
        for step in _topo_order(plan):
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
            # Cascade skip: a step whose dependency was skipped is skipped
            # too — no data, no run. Topo order guarantees the dependency
            # was already processed, so `skipped` is complete here.
            blocked_by = next((d for d in step.depends_on if d in skipped), None)
            if blocked_by is not None:
                sr.skipped = True
                sr.skip_reason = f"dependency '{blocked_by}' was skipped"
                skipped.add(step.var)
                env[step.var] = None
                sr.outputs_digest = _digest(None)
                receipt.steps.append(sr)
                continue
            try:
                self._execute_step(step, op, env, sr, args)
            except _Suspended:
                receipt.steps.append(sr)
                receipt.status = "suspended"
                break
            except _Denied:
                receipt.steps.append(sr)
                receipt.status = "denied"
                break
            if sr.skipped:
                skipped.add(step.var)

            receipt.tokens_used += sr.tokens_in + sr.tokens_out
            receipt.steps.append(sr)

        self._apply_budget_audits(receipt)
        return receipt

    def _execute_step(
        self,
        step: PlanStep,
        op: Op,
        env: dict[str, Any],
        sr: StepReceipt,
        args: list[Any],
    ) -> None:
        """Run one step: fan out over list args, when-filter, or a single call."""
        if len(args) == 1 and isinstance(args[0], list):
            self._execute_fanout(step, op, env, sr, args[0])
        elif step.when and not ir_evaluator.evaluate(
            step.when, dict(zip(step.args, args))
        ):
            sr.skipped = True
            sr.skip_reason = "when condition false"
            env[step.var] = None
        else:
            self._execute_single(step, op, env, sr, args)
        sr.outputs_digest = _digest(env[step.var])

    def _execute_fanout(
        self,
        step: PlanStep,
        op: Op,
        env: dict[str, Any],
        sr: StepReceipt,
        items: list[Any],
    ) -> None:
        """A list arg fans out: optional when-filter, then one call per element."""
        if step.when:
            items = [
                it
                for it in items
                if ir_evaluator.evaluate(step.when, {step.args[0]: it})
            ]
        outputs = [self._call(op, it, sr) for it in items]
        env[step.var] = [o for o in outputs if not isinstance(o, _Dropped)]

    def _execute_single(
        self,
        step: PlanStep,
        op: Op,
        env: dict[str, Any],
        sr: StepReceipt,
        args: list[Any],
    ) -> None:
        """A scalar step: one call; a rejecting gate verdict drops the item."""
        arg = args[0] if len(args) == 1 else args
        out = self._call(op, arg, sr)
        if isinstance(out, _Dropped):
            sr.dropped = True
            env[step.var] = None
        else:
            env[step.var] = out

    def _apply_budget_audits(self, receipt: RunReceipt) -> None:
        """Budget audits (suspend/deny) run after the plan; failures are recorded."""
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
                    if not ir_evaluator.evaluate(audit.expr, metrics):
                        receipt.audit_failures.append(audit.name)
                except Exception as e:  # noqa: BLE001 - eval failure IS an audit failure
                    receipt.audit_failures.append(f"{audit.name} (eval error: {e})")

    def _call(self, op: Op, inputs: Any, sr: StepReceipt) -> Any:
        """Dispatch one op call by effect lane."""
        if op.effect in (Effect.PURE, Effect.RECORDED):
            fn = self.op_impls.get(op.name)
            if fn is None:
                raise ValueError(f"no implementation for op '{op.name}'")
            return fn(inputs)
        if op.effect == Effect.EXTERNAL:
            return self._call_external(op, inputs, sr)
        if op.effect == Effect.SUSPEND:
            raise _Suspended(f"op '{op.name}' suspends")
        raise ValueError(f"unknown effect {op.effect}")

    def _ask_gate(self, op: Op, inputs: Any, sr: StepReceipt) -> str:
        """Ask the human for a gate verdict; records gate and verdict on the receipt."""
        gate = self.gates[op.gate]
        verdict = ""
        if self.gate_io is not None:
            verdict = self.gate_io.ask_verdict(gate, inputs) or ""
        sr.gate = gate.name
        sr.verdict = verdict
        return verdict

    def _call_external(self, op: Op, inputs: Any, sr: StepReceipt) -> Any:
        """External op: deny list, human gate, shadow mode, then the model call."""
        if self._denied(op) and not op.gate:
            raise _Denied(f"op '{op.name}' denied by spec deny list")

        if op.gate:
            verdict = self._ask_gate(op, inputs, sr)
            if not verdict:
                sr.suspended = True
                raise _Suspended(f"gate '{op.gate}' awaiting verdict")
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
