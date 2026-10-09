"""Round-trip: the canonical text form is stable and lossless."""

from __future__ import annotations

from pathlib import Path

from ir import (
    AuditRule,
    Effect,
    Field,
    Gate,
    Op,
    Plan,
    PlanStep,
    Spec,
    TypeDef,
    check,
    dumps,
    loads,
)


def _mini_spec() -> Spec:
    return Spec(
        name="mini",
        version="v1",
        author="david@local",
        goal="prove the round trip",
        budget_tokens=100,
        budget_human_minutes=5,
        effects=["model.complete"],
        deny=["action.execute"],
        types=[TypeDef("item", [Field("title", "text"), Field("score", "float")])],
        ops=[
            Op(
                name="score_item",
                params=["item"],
                returns="item",
                effect=Effect.EXTERNAL,
                capability="model.complete",
                using="fit_v1",
                using_kind="prompt",
            ),
            Op(
                name="send",
                params=["item"],
                returns="receipt",
                effect=Effect.EXTERNAL,
                capability="action.execute",
                gate="approval",
            ),
        ],
        gates=[Gate("approval", ["approve", "reject"])],
        audits=[AuditRule("budget_tokens", "tokens_used <= 100", "suspend")],
        plans=[
            Plan(
                "main",
                [
                    PlanStep("s", "score_item", ["item"]),
                    PlanStep("r", "send", ["s"], when="s.score > 0.5"),
                ],
            )
        ],
    )


def test_round_trip():
    spec = _mini_spec()
    assert loads(dumps(spec)) == spec


def test_canonical_is_stable():
    spec = _mini_spec()
    assert dumps(loads(dumps(spec))) == dumps(spec)


def test_opportunity_pipeline_example_is_valid():
    path = Path(__file__).parent.parent / "examples" / "ir" / "opportunity_pipeline.ir"
    spec = loads(path.read_text())
    assert spec.name == "opportunity_pipeline"
    assert check(spec) == []
    # the scoring step uses a prompt; the checker is right —
    # a prompt means a model call means external.
    extract = next(o for o in spec.ops if o.name == "extract_scored")
    assert extract.effect == Effect.EXTERNAL
    assert extract.using == "job_fit_v1"
    # no gate: it's a list; the deny list is the safety scope.
    assert spec.gates == []
    assert "action.execute" in spec.deny
