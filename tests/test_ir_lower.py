"""Lowering: the DSL skin compiles down to IR ops. Nothing is lost,
nothing extra is smuggled in — SET (model/temperature/seed) is binding
config and must not appear in the durable definition."""

from __future__ import annotations

from pathlib import Path

from aidsl.parser import parse
from ir import check, dumps, lower_program


def _showcase():
    path = Path(__file__).parent.parent / "examples" / "showcase.ai"
    return parse(str(path))


def test_lower_showcase_types():
    spec = lower_program(_showcase(), name="showcase", version="v1")
    types = {t.name: t for t in spec.types}
    assert set(types) >= {"claim", "line_item", "draft"}
    claim_fields = {f.name: f.type for f in types["claim"].fields}
    assert claim_fields["claim_amount"] == "money"
    assert claim_fields["is_disputed"] == "bool"
    assert claim_fields["claim_type"] == "enum[auto, property, health, liability]"
    assert claim_fields["items"] == "line_item[]"


def test_lower_showcase_ops():
    spec = lower_program(_showcase(), name="showcase", version="v1")
    ops = {o.name: o for o in spec.ops}
    assert set(ops) >= {"extract_claim", "draft_response", "write_output"}
    assert ops["extract_claim"].effect.value == "external"
    assert ops["extract_claim"].capability == "model.complete"
    assert ops["extract_claim"].using_kind == "prompt"
    assert ops["write_output"].effect.value == "recorded"


def test_lower_showcase_flags_become_audits():
    spec = lower_program(_showcase(), name="showcase", version="v1")
    audits = {a.name: a for a in spec.audits}
    assert audits["flag_1"].expr == "claim_amount > 10000"
    assert audits["flag_2"].expr == "is_disputed == true"
    assert audits["flag_3"].expr == 'claim_type == "liability" and claim_amount > 5000'
    assert all(a.action == "flag" for a in audits.values())


def test_lower_showcase_plan_threads():
    spec = lower_program(_showcase(), name="showcase", version="v1")
    assert len(spec.plans) == 1
    steps = spec.plans[0].steps
    assert [s.op for s in steps] == [
        "extract_claim",
        "draft_response",
        "write_output",
    ]
    # each step feeds the next
    assert steps[1].args == [steps[0].var]
    assert steps[2].args == [steps[1].var]


def test_set_is_binding_config_not_ir():
    """Model choice must not change the durable definition."""
    spec = lower_program(_showcase(), name="showcase", version="v1")
    text = dumps(spec)
    assert "gpt-4.1" not in text
    assert "temperature" not in text.lower()
    assert "seed" not in text.lower()


def test_lowered_dsl_needs_gates():
    """Honest gap the checker catches: the DSL has no gate/deny concept,
    so its external ops arrive unconstrained. IR-04 says so out loud."""
    spec = lower_program(_showcase(), name="showcase", version="v1")
    violations = check(spec)
    assert violations, "expected IR-04 violations for gateless external ops"
    assert all(v.code == "IR-04" for v in violations)
    assert {v.message.split("'")[1] for v in violations} == {
        "extract_claim",
        "draft_response",
    }
