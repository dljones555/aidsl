"""Receipt card: a run record renders as a stakeholder-readable card."""

from __future__ import annotations

from ir import RunReceipt, StepReceipt, render_card


def _receipt() -> RunReceipt:
    return RunReceipt(
        spec="opportunity_pipeline",
        version="v1",
        plan="daily_match",
        status="completed",
        tokens_used=120,
        human_minutes_used=5,
        steps=[
            StepReceipt(
                var="postings",
                op="fetch",
                effect="recorded",
                inputs_digest="aa01",
                outputs_digest="bb02",
            ),
            StepReceipt(
                var="scored",
                op="classify",
                effect="external",
                inputs_digest="cc03",
                outputs_digest="dd04",
                tokens_in=40,
                tokens_out=80,
                gate="lead_gate",
                verdict="approve",
                flags=["stale_posting"],
            ),
            StepReceipt(
                var="draft",
                op="write",
                effect="pure",
                inputs_digest="ee05",
                outputs_digest="ff06",
                skipped=True,
            ),
        ],
    )


def test_card_names_the_plan():
    card = render_card(_receipt())
    assert "daily_match" in card


def test_card_shows_each_step_outcome():
    card = render_card(_receipt())
    assert "postings = fetch (recorded) — completed" in card
    assert "scored = classify (external) — completed" in card
    assert "stale_posting" in card
    assert "draft = write (pure) — skipped" in card


def test_card_shows_the_human_decision():
    card = render_card(_receipt())
    assert "lead_gate" in card
    assert "approve" in card


def test_card_shows_the_cost_line():
    card = render_card(_receipt())
    assert "tokens used: 120" in card
    assert "human minutes: 5" in card


def test_card_shows_model_output_when_supplied():
    card = render_card(
        _receipt(),
        outputs={"scored": {"title": "Line Cook", "score": 0.85}},
    )
    assert "Line Cook" in card
    assert "0.85" in card


def test_card_is_deterministic():
    assert render_card(_receipt()) == render_card(_receipt())
