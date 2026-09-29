"""Executor: the contract runs. Gates suspend, deny blocks, audits bite."""

from __future__ import annotations

import json
from pathlib import Path

from ir import (
    AuditRule,
    AutoVerdict,
    CannedModel,
    Effect,
    Executor,
    Field,
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


def _fetch(_inputs):
    path = ROOT / "examples" / "ir" / "postings.jsonl"
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


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

DRAFTS = [
    {
        "to": "jobs@ cannery.example",
        "subject": "Line cook application",
        "body": "Hi, ...",
    },
    {
        "to": "jobs@sprouts.example",
        "subject": "Overnight stocker application",
        "body": "Hi, ...",
    },
    {"to": "jobs@mamas.example", "subject": "Busser application", "body": "Hi, ..."},
    {
        "to": "jobs@coast.example",
        "subject": "Event crew application",
        "body": "Hi, ...",
    },
]


def _model():
    return CannedModel(
        {
            "classify_posting": [ModelResult(d, 120, 40) for d in SCORED],
            "draft_outreach": [ModelResult(d, 100, 60) for d in DRAFTS],
        }
    )


def test_run_suspends_at_gate():
    ex = Executor(
        _example_spec(),
        _model(),
        op_impls={"fetch_boards": _fetch},
        gate_io=SuspendAlways(),
    )
    receipt = ex.run("daily_scan")
    assert receipt.status == "suspended"
    gate_step = receipt.steps[-1]
    assert gate_step.op == "send_outreach"
    assert gate_step.suspended and gate_step.gate == "approval"
    # the when-filter kept only fit, non-excluded postings
    draft_step = next(s for s in receipt.steps if s.op == "draft_outreach")
    assert draft_step.tokens_in == 4 * 100  # 4 drafts, not 6
    assert receipt.tokens_used == 6 * 160 + 4 * 160


def test_approve_hits_shadow_mode():
    """deny: action.execute — the send exists in the spec but cannot run."""
    ex = Executor(
        _example_spec(),
        _model(),
        op_impls={"fetch_boards": _fetch},
        gate_io=AutoVerdict("approve"),
    )
    receipt = ex.run("daily_scan")
    assert receipt.status == "completed"
    send = receipt.steps[-1]
    assert send.verdict == "approve"
    assert send.shadow_blocked
    assert receipt.human_minutes_used == 5
    assert receipt.audit_failures == []


def test_reject_drops_the_send():
    ex = Executor(
        _example_spec(),
        _model(),
        op_impls={"fetch_boards": _fetch},
        gate_io=AutoVerdict("reject"),
    )
    receipt = ex.run("daily_scan")
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


def test_run_is_deterministic():
    def run_once():
        ex = Executor(
            _example_spec(),
            _model(),
            op_impls={"fetch_boards": _fetch},
            gate_io=AutoVerdict("approve"),
        )
        return ex.run("daily_scan").to_dict()

    assert run_once() == run_once()
