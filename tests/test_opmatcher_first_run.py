"""Story 1 (PBI #38): the opportunity pipeline loads, checks, and runs.

Fast, deterministic, no files: CannedModel on a tiny inline fixture.
The FileModel/file path is covered by examples/run_opportunity_scan.py.
"""

from __future__ import annotations

from pathlib import Path

from ir import (
    AutoVerdict,
    CannedModel,
    Executor,
    ModelResult,
    SuspendAlways,
    check,
    loads,
    render_card,
)

ROOT = Path(__file__).parent.parent


def _tiny_fixture() -> tuple[list[dict], list[ModelResult], list[ModelResult]]:
    """Two postings: one fit, one excluded. Minimal but exercises the when."""
    postings = [
        {"title": "Busser", "pay": "$17/hr", "employer": "M", "url": "u1"},
        {"title": "Manager", "pay": "$95k/yr", "employer": "G", "url": "u2"},
    ]
    scored = [
        ModelResult({"title": "Busser", "score": 0.8, "excluded": False}, 10, 5),
        ModelResult({"title": "Manager", "score": 0.2, "excluded": True}, 10, 5),
    ]
    drafts = [ModelResult({"to": "jobs@m.example", "subject": "Busser"}, 8, 4)]
    return postings, scored, drafts


def _run(verdict: str | None):
    spec = loads((ROOT / "examples" / "ir" / "opportunity_pipeline.ir").read_text())
    assert check(spec) == []
    postings, scored, drafts = _tiny_fixture()
    model = CannedModel({"classify_posting": scored, "draft_outreach": drafts})
    gate_io = AutoVerdict(verdict) if verdict else SuspendAlways()
    executor = Executor(
        spec,
        model,
        op_impls={"fetch_boards": lambda _inputs: postings},
        gate_io=gate_io,
    )
    return executor.run("daily_scan")


def test_pipeline_loads_checks_and_runs_to_approval():
    """End-to-end with CannedModel: approve -> completed, send shadow-blocked."""
    receipt = _run("approve")
    assert receipt.status == "completed"
    assert [s.var for s in receipt.steps] == ["p", "s", "d", "r"]
    send = receipt.steps[-1]
    assert send.verdict == "approve"
    assert send.shadow_blocked  # deny: action.execute keeps it out of prod
    assert receipt.audit_failures == []


def test_pipeline_suspends_without_verdict():
    """No verdict -> the run waits at the human gate instead of guessing."""
    receipt = _run(None)
    assert receipt.status == "suspended"
    gate_step = receipt.steps[-1]
    assert gate_step.op == "send_outreach"
    assert gate_step.suspended


def test_receipt_card_renders_for_run():
    """render_card produces the user-presentable proof of the run."""
    receipt = _run("approve")
    card = render_card(receipt)
    assert card.startswith("# Verify receipt — daily_scan")
    assert "send_outreach" in card
    assert "approve" in card
    assert card.endswith("\n") and not card.endswith("\n\n")
