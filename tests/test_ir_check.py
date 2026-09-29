"""Checker: every rule earns its keep with a failing case."""

from __future__ import annotations

from ir import (
    AuditRule,
    Effect,
    Op,
    Plan,
    PlanStep,
    Spec,
    check,
)


def _valid_op(**kw) -> Op:
    base = {
        "name": "fetch",
        "params": [],
        "returns": "receipt",
        "effect": Effect.RECORDED,
        "capability": "fs.read",
    }
    base.update(kw)
    return Op(**base)


def test_ir01_undefined_op_in_plan():
    spec = Spec(
        name="s",
        ops=[_valid_op()],
        plans=[Plan("main", [PlanStep("x", "ghost", [])])],
    )
    vs = check(spec)
    assert [v.code for v in vs] == ["IR-01"]


def test_ir02_undefined_gate():
    spec = Spec(
        name="s",
        deny=["action.execute"],
        ops=[
            Op(
                name="send",
                returns="receipt",
                effect=Effect.EXTERNAL,
                capability="action.execute",
                gate="nope",
            )
        ],
    )
    assert [v.code for v in check(spec)] == ["IR-02"]


def test_ir03_undefined_return_type():
    spec = Spec(name="s", deny=["x"], ops=[_valid_op(name="f", returns="nonsense")])
    assert [v.code for v in check(spec)] == ["IR-03"]


def test_ir04_external_without_gate_or_deny():
    spec = Spec(
        name="s",
        ops=[
            Op(
                name="send",
                returns="receipt",
                effect=Effect.EXTERNAL,
                capability="action.execute",
            )
        ],
    )
    vs = check(spec)
    assert [v.code for v in vs] == ["IR-04"]
    assert "send" in vs[0].message


def test_ir04_satisfied_by_deny():
    spec = Spec(
        name="s",
        deny=["action.execute"],
        ops=[
            Op(
                name="send",
                returns="receipt",
                effect=Effect.EXTERNAL,
                capability="action.execute",
            )
        ],
    )
    assert check(spec) == []


def test_ir05_pure_op_with_prompt():
    spec = Spec(
        name="s",
        deny=["x"],
        ops=[
            Op(
                name="match",
                returns="receipt",
                effect=Effect.PURE,
                using="some_prompt",
                using_kind="prompt",
            )
        ],
    )
    vs = check(spec)
    assert [v.code for v in vs] == ["IR-05"]


def test_ir06_ir07_bad_audit():
    spec = Spec(
        name="s",
        deny=["x"],
        ops=[_valid_op()],
        audits=[
            AuditRule("a1", "tokens_used <= 10", "explode"),
            AuditRule("a2", "(((broken", "flag"),
        ],
    )
    codes = sorted(v.code for v in check(spec))
    assert codes == ["IR-06", "IR-07"]


def test_ir08_duplicate_op():
    spec = Spec(name="s", deny=["x"], ops=[_valid_op(), _valid_op()])
    assert [v.code for v in check(spec)] == ["IR-08"]


def test_ir09_bad_when_clause():
    spec = Spec(
        name="s",
        deny=["x"],
        ops=[_valid_op()],
        plans=[Plan("main", [PlanStep("x", "fetch", [], when="(((broken")])],
    )
    assert [v.code for v in check(spec)] == ["IR-09"]
