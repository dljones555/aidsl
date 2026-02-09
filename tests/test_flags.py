from __future__ import annotations

from aidsl.compiler import FlagEvaluator
from aidsl.parser import FlagRule, Condition


def _evaluator(*rules: FlagRule) -> FlagEvaluator:
    return FlagEvaluator(rules=list(rules))


def test_flag_over_triggers():
    ev = _evaluator(FlagRule([Condition("amount", "OVER", "500")]))
    reasons = ev.evaluate({"amount": 600})
    assert len(reasons) == 1
    assert "amount OVER 500" in reasons[0]


def test_flag_over_does_not_trigger():
    ev = _evaluator(FlagRule([Condition("amount", "OVER", "500")]))
    reasons = ev.evaluate({"amount": 100})
    assert len(reasons) == 0


def test_flag_over_boundary():
    ev = _evaluator(FlagRule([Condition("amount", "OVER", "500")]))
    assert ev.evaluate({"amount": 500}) == []  # not strictly over
    assert len(ev.evaluate({"amount": 500.01})) == 1


def test_flag_under():
    ev = _evaluator(FlagRule([Condition("amount", "UNDER", "10")]))
    assert len(ev.evaluate({"amount": 5})) == 1
    assert ev.evaluate({"amount": 20}) == []


def test_flag_is():
    ev = _evaluator(FlagRule([Condition("category", "IS", "travel")]))
    assert len(ev.evaluate({"category": "travel"})) == 1
    assert ev.evaluate({"category": "meals"}) == []


def test_flag_is_case_insensitive():
    ev = _evaluator(FlagRule([Condition("category", "IS", "travel")]))
    assert len(ev.evaluate({"category": "Travel"})) == 1


def test_flag_and_both_true():
    rule = FlagRule(
        [Condition("category", "IS", "travel"), Condition("amount", "OVER", "200")],
        ["AND"],
    )
    ev = _evaluator(rule)
    assert len(ev.evaluate({"category": "travel", "amount": 300})) == 1


def test_flag_and_one_false():
    rule = FlagRule(
        [Condition("category", "IS", "travel"), Condition("amount", "OVER", "200")],
        ["AND"],
    )
    ev = _evaluator(rule)
    assert ev.evaluate({"category": "travel", "amount": 100}) == []
    assert ev.evaluate({"category": "meals", "amount": 300}) == []


def test_flag_or():
    rule = FlagRule(
        [Condition("amount", "OVER", "500"), Condition("category", "IS", "travel")],
        ["OR"],
    )
    ev = _evaluator(rule)
    assert len(ev.evaluate({"amount": 600, "category": "meals"})) == 1
    assert len(ev.evaluate({"amount": 100, "category": "travel"})) == 1
    assert ev.evaluate({"amount": 100, "category": "meals"}) == []


def test_flag_missing_field():
    ev = _evaluator(FlagRule([Condition("amount", "OVER", "500")]))
    assert ev.evaluate({}) == []


def test_multiple_rules():
    ev = _evaluator(
        FlagRule([Condition("amount", "OVER", "500")]),
        FlagRule([Condition("category", "IS", "travel")]),
    )
    reasons = ev.evaluate({"amount": 600, "category": "travel"})
    assert len(reasons) == 2


def test_multiple_rules_partial():
    ev = _evaluator(
        FlagRule([Condition("amount", "OVER", "500")]),
        FlagRule([Condition("category", "IS", "travel")]),
    )
    reasons = ev.evaluate({"amount": 600, "category": "meals"})
    assert len(reasons) == 1
