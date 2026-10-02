"""depends_on: ordering and concurrency permission from one declaration."""

from __future__ import annotations

import pytest

from ir import (
    CannedModel,
    Effect,
    Executor,
    Op,
    Plan,
    PlanStep,
    Spec,
    check,
    dumps,
    loads,
)


def _dag_spec(step_defs: list[tuple[str, list[str]]]) -> Spec:
    """Build a spec from (var, depends_on) pairs.

    Each step calls op_<var> with its dependencies as args — the
    declaration does double duty for data flow and ordering.
    """
    steps = [
        PlanStep(var, f"op_{var}", list(deps), depends_on=list(deps))
        for var, deps in step_defs
    ]
    ops = [
        Op(name=f"op_{var}", returns="receipt", effect=Effect.PURE)
        for var, _ in step_defs
    ]
    return Spec(name="s", ops=ops, plans=[Plan("main", steps)])


def _run_order(spec: Spec) -> list[str]:
    """Run a spec of pure ops; return the vars in execution order."""
    order: list[str] = []

    def recorder(var: str):
        def impl(inputs):
            order.append(var)
            return f"val_{var}"  # a scalar: a list would trigger fan-out

        return impl

    impls = {f"op_{s.var}": recorder(s.var) for s in spec.plans[0].steps}
    Executor(spec, CannedModel({}), op_impls=impls).run()
    return order


def test_diamond_runs_in_topo_order():
    # Listed out of order on purpose: d, b, c, a.
    spec = _dag_spec(
        [
            ("d", ["b", "c"]),
            ("b", ["a"]),
            ("c", ["a"]),
            ("a", []),
        ]
    )
    assert check(spec) == []
    order = _run_order(spec)
    assert order[0] == "a"  # the root always runs first
    assert order[-1] == "d"  # the sink always runs last
    assert set(order[1:3]) == {"b", "c"}  # the middle pair in either order


def test_no_depends_on_keeps_listed_order():
    spec = _dag_spec([("c", []), ("a", []), ("b", [])])
    assert check(spec) == []
    assert _run_order(spec) == ["c", "a", "b"]


def test_ir10_unknown_dependency():
    spec = _dag_spec([("b", ["ghost"]), ("a", [])])
    vs = check(spec)
    assert [v.code for v in vs] == ["IR-10"]
    assert "ghost" in vs[0].message


def test_ir11_dependency_cycle():
    spec = _dag_spec([("a", ["b"]), ("b", ["a"])])
    vs = check(spec)
    assert [v.code for v in vs] == ["IR-11"]
    assert "cycle" in vs[0].message


def test_ir11_self_dependency_is_a_cycle():
    spec = _dag_spec([("a", ["a"])])
    assert [v.code for v in check(spec)] == ["IR-11"]


def test_executor_rejects_bad_graph_loudly():
    with pytest.raises(ValueError, match="unknown step 'ghost'"):
        _run_order(_dag_spec([("b", ["ghost"]), ("a", [])]))
    with pytest.raises(ValueError, match="dependency cycle"):
        _run_order(_dag_spec([("a", ["b"]), ("b", ["a"])]))


def test_depends_on_survives_round_trip():
    spec = _dag_spec([("d", ["b", "c"]), ("b", ["a"]), ("c", ["a"]), ("a", [])])
    text = dumps(spec)
    assert "depends_on b, c" in text
    assert loads(text) == spec
