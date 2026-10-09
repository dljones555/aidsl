"""Executor: the contract runs. Gates suspend, deny blocks, audits bite."""

from __future__ import annotations

from pathlib import Path

from ir import (
    AuditRule,
    AutoVerdict,
    CannedModel,
    Effect,
    Executor,
    Field,
    Gate,
    ModelResult,
    Op,
    Plan,
    PlanStep,
    Spec,
    SuspendAlways,
    TypeDef,
    check,
    loads,
)

ROOT = Path(__file__).parent.parent


def _example_spec() -> Spec:
    spec = loads((ROOT / "examples" / "ir" / "opportunity_pipeline.ir").read_text())
    assert check(spec) == []
    return spec


SCORED = [
    {
        "title": "Line Cook — The Cannery",
        "pay": "$19/hr",
        "employer": "The Cannery Restaurant",
        "url": "u1",
        "score": 0.85,
        "excluded": False,
    },
    {
        "title": "Delivery Driver — Pizza Place",
        "pay": "$18/hr + tips",
        "employer": "Slice House",
        "url": "u2",
        "score": 0.4,
        "excluded": True,
    },
    {
        "title": "Grocery Stocker (Overnight)",
        "pay": "$20.50/hr",
        "employer": "Sprouts",
        "url": "u3",
        "score": 0.9,
        "excluded": False,
    },
    {
        "title": "Marketing Manager — DTC Brand",
        "pay": "$95k/yr",
        "employer": "GlowCo",
        "url": "u4",
        "score": 0.2,
        "excluded": True,
    },
    {
        "title": "Busser — Weekend Brunch",
        "pay": "$17/hr + tips",
        "employer": "Mama's Kitchen",
        "url": "u5",
        "score": 0.75,
        "excluded": False,
    },
    {
        "title": "Event Setup Crew",
        "pay": "$22/hr",
        "employer": "Coast Events",
        "url": "u6",
        "score": 0.8,
        "excluded": False,
    },
]


def _model():
    return CannedModel({"extract_scored": [ModelResult(d, 120, 40) for d in SCORED]})


def test_run_is_deterministic():
    def run_once():
        ex = Executor(
            _example_spec(),
            _model(),
            op_impls={"write_output": lambda item: {"ok": True}},
        )
        return ex.run("main").to_dict()

    assert run_once() == run_once()


def _gated_spec() -> Spec:
    """Minimal inline spec with a human gate: keeps the executor's
    gate/shadow semantics covered now that the example pipeline is a
    gateless list."""
    return Spec(
        name="gated",
        version="v1",
        deny=["action.execute"],
        types=[TypeDef("t", [Field("x", "text")])],
        ops=[
            Op(
                name="fetch",
                returns="t",
                effect=Effect.RECORDED,
                capability="fs.read",
            ),
            Op(
                name="act",
                returns="t",
                effect=Effect.EXTERNAL,
                capability="action.execute",
                gate="approval",
            ),
        ],
        gates=[Gate("approval", verdicts=["approve", "edit", "reject"])],
        plans=[
            Plan(
                "main",
                [
                    PlanStep("f", "fetch", []),
                    PlanStep("r", "act", ["f"]),
                ],
            )
        ],
    )


def test_run_suspends_at_gate():
    ex = Executor(
        _gated_spec(),
        CannedModel({}),
        op_impls={"fetch": lambda _inputs: {"x": "y"}},
        gate_io=SuspendAlways(),
    )
    receipt = ex.run("main")
    assert receipt.status == "suspended"
    gate_step = receipt.steps[-1]
    assert gate_step.op == "act"
    assert gate_step.suspended and gate_step.gate == "approval"


def test_approve_hits_shadow_mode():
    """deny: action.execute — the act exists in the spec but cannot run."""
    ex = Executor(
        _gated_spec(),
        CannedModel({}),
        op_impls={"fetch": lambda _inputs: {"x": "y"}},
        gate_io=AutoVerdict("approve"),
    )
    receipt = ex.run("main")
    assert receipt.status == "completed"
    act = receipt.steps[-1]
    assert act.verdict == "approve"
    assert act.shadow_blocked
    assert receipt.human_minutes_used == 5
    assert receipt.audit_failures == []


def test_reject_drops_the_send():
    ex = Executor(
        _gated_spec(),
        CannedModel({}),
        op_impls={"fetch": lambda _inputs: {"x": "y"}},
        gate_io=AutoVerdict("reject"),
    )
    receipt = ex.run("main")
    assert receipt.status == "completed"
    assert receipt.steps[-1].verdict == "reject"


def test_deny_without_gate_stops_run():
    spec = Spec(
        name="s",
        version="v1",
        deny=["model.complete"],
        types=[TypeDef("t", [Field("x", "text")])],
        ops=[
            Op(
                name="do_it",
                returns="t",
                effect=Effect.EXTERNAL,
                capability="model.complete",
            )
        ],
        plans=[Plan("main", [PlanStep("y", "do_it", [])])],
    )
    ex = Executor(spec, CannedModel({}))
    receipt = ex.run()
    assert receipt.status == "denied"


def test_budget_audit_bites():
    spec = Spec(
        name="s",
        version="v1",
        deny=["model.complete"],
        types=[TypeDef("t", [Field("x", "text")])],
        ops=[
            Op(
                name="spend",
                returns="t",
                effect=Effect.EXTERNAL,
                capability="other",
            )
        ],
        audits=[AuditRule("budget_tokens", "tokens_used <= 5", "suspend")],
        plans=[Plan("main", [PlanStep("y", "spend", [])])],
    )
    ex = Executor(spec, CannedModel({"spend": {"x": "y"}}))
    receipt = ex.run()
    assert receipt.status == "completed"
    assert receipt.audit_failures == ["budget_tokens"]


def test_file_model_consumes_entries_in_order(tmp_path):
    """Super-muse mode: each response is served once, in file order."""
    from ir import FileModel, NeedModelResponse

    path = tmp_path / "responses.jsonl"
    path.write_text('{"op": "a", "data": {"n": 1}}\n{"op": "a", "data": {"n": 2}}\n')
    model = FileModel(path)
    assert model.complete(op="a", prompt="p", schema={}).data == {"n": 1}
    assert model.complete(op="a", prompt="p", schema={}).data == {"n": 2}
    try:
        model.complete(op="a", prompt="p", schema={})
        raise AssertionError("should have raised NeedModelResponse")
    except NeedModelResponse as e:
        assert e.op == "a"
