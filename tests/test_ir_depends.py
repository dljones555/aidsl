"""depends_on: ordering and concurrency permission from one declaration."""

from __future__ import annotations

import pytest

from ir import (
    AutoVerdict,
    CannedModel,
    Effect,
    Executor,
    Gate,
    Op,
    Plan,
    PlanStep,
    Spec,
    SuspendAlways,
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


# --- Graph shapes borrowed from the comparables ---------------------------
# CPython's test_graphlib.py and networkx's test_dag.py both cover: long
# chains, disconnected components, duplicate edges, empty graphs, and
# indirect cycles. The same shapes apply here, through the IR's own
# vocabulary (IR-10/IR-11, listed-order stability).


def test_long_chain_runs_in_exact_order():
    spec = _dag_spec(
        [
            ("e", ["d"]),
            ("d", ["c"]),
            ("c", ["b"]),
            ("b", ["a"]),
            ("a", []),
        ]
    )
    assert check(spec) == []
    assert _run_order(spec) == ["a", "b", "c", "d", "e"]


def test_wide_fan_in_sink_runs_last():
    spec = _dag_spec(
        [
            ("sink", ["r1", "r2", "r3", "r4"]),
            ("r1", []),
            ("r2", []),
            ("r3", []),
            ("r4", []),
        ]
    )
    assert check(spec) == []
    order = _run_order(spec)
    assert order[-1] == "sink"
    assert order[:-1] == ["r1", "r2", "r3", "r4"]  # stability, not luck


def test_wide_fan_out_consumers_follow_producer():
    spec = _dag_spec(
        [
            ("c1", ["p"]),
            ("c2", ["p"]),
            ("c3", ["p"]),
            ("p", []),
        ]
    )
    assert check(spec) == []
    order = _run_order(spec)
    assert order[0] == "p"
    assert order[1:] == ["c1", "c2", "c3"]  # stability, not luck


def test_disconnected_components_keep_internal_order():
    # Two independent chains, listed interleaved: x, a, y, b.
    spec = _dag_spec([("x", []), ("a", []), ("y", ["x"]), ("b", ["a"])])
    assert check(spec) == []
    order = _run_order(spec)
    assert order.index("x") < order.index("y")
    assert order.index("a") < order.index("b")
    assert order == ["x", "a", "y", "b"]  # stability across components


def test_duplicate_dependencies_are_idempotent():
    spec = _dag_spec([("b", ["a", "a"]), ("a", [])])
    assert check(spec) == []
    assert _run_order(spec) == ["a", "b"]


def test_empty_plan_runs():
    spec = Spec(name="s", plans=[Plan("main", [])])
    assert check(spec) == []
    receipt = Executor(spec, CannedModel({})).run()
    assert receipt.status == "completed"
    assert receipt.steps == []


def test_ir11_indirect_cycle_shows_path():
    spec = _dag_spec([("a", ["b"]), ("b", ["c"]), ("c", ["a"])])
    vs = check(spec)
    assert [v.code for v in vs] == ["IR-11"]
    assert "a -> b -> c -> a" in vs[0].message


# --- depends_on composed with executor semantics ---------------------------


def test_depends_on_with_when_condition():
    """depends_on orders; when filters. A skipped step keeps its topo slot."""
    steps = [
        PlanStep("d", "op_d", ["b"], when="b == 'keep'", depends_on=["b"]),
        PlanStep("c", "op_c", ["b"], when="b == 'skip'", depends_on=["b"]),
        PlanStep("b", "op_b", ["a"], depends_on=["a"]),
        PlanStep("a", "op_a", [], depends_on=[]),
    ]
    ops = [Op(f"op_{v}", effect=Effect.PURE) for v in "abcd"]
    spec = Spec(name="s", ops=ops, plans=[Plan("main", steps)])
    assert check(spec) == []

    ran: list[str] = []

    def impl(var: str):
        def fn(_inputs):
            ran.append(var)
            return "go" if var == "a" else "keep"

        return fn

    receipt = Executor(
        spec, CannedModel({}), op_impls={f"op_{v}": impl(v) for v in "abcd"}
    ).run()
    assert ran == ["a", "b", "d"]  # c evaluated its when and stood down
    by_var = {s.var: s for s in receipt.steps}
    assert by_var["c"].skipped
    assert not by_var["d"].skipped


def test_depends_on_orders_fanned_consumer():
    """A producer returning a list fans the consumer out; the DAG still orders."""
    calls: list = []

    def _produce(_inputs):
        calls.append("produce")
        return [1, 2, 3]

    def _consume(item):
        calls.append(("consume", item))
        return item * 10

    spec = Spec(
        name="s",
        ops=[
            Op("produce", effect=Effect.PURE),
            Op("consume", effect=Effect.PURE),
        ],
        plans=[
            Plan(
                "main",
                [
                    PlanStep("out", "consume", ["nums"], depends_on=["nums"]),
                    PlanStep("nums", "produce", [], depends_on=[]),
                ],
            )
        ],
    )
    assert check(spec) == []
    Executor(
        spec, CannedModel({}), op_impls={"produce": _produce, "consume": _consume}
    ).run()
    assert calls[0] == "produce"
    assert calls[1:] == [("consume", 1), ("consume", 2), ("consume", 3)]


# --- Realistic plans across effect classes ---------------------------------
# What real depends_on code looks like: recorded fetches, external model
# calls, and a human gate, with the steps listed out of order on purpose.


def _pipeline_spec() -> Spec:
    """fetch (RECORDED) -> classify (EXTERNAL) -> approve (EXTERNAL + gate)
    -> summarize (EXTERNAL) -> notify (RECORDED). Listed out of order: the
    DAG, not the listing, decides."""
    ops = [
        Op("fetch_board", effect=Effect.RECORDED),
        Op("classify_board", effect=Effect.EXTERNAL, capability="model.complete"),
        Op(
            "approve_send",
            effect=Effect.EXTERNAL,
            capability="model.complete",
            gate="approval",
        ),
        Op("summarize_batch", effect=Effect.EXTERNAL, capability="model.complete"),
        Op("notify_owner", effect=Effect.RECORDED),
    ]
    steps = [
        PlanStep("notify", "notify_owner", ["summary"], depends_on=["summary"]),
        PlanStep("summary", "summarize_batch", ["verdict"], depends_on=["verdict"]),
        PlanStep("verdict", "approve_send", ["top"], depends_on=["top"]),
        PlanStep("top", "classify_board", ["board"], depends_on=["board"]),
        PlanStep("board", "fetch_board", [], depends_on=[]),
    ]
    return Spec(
        name="pipeline",
        version="v1",
        # Shadow-mode backstop; also satisfies IR-04 for the gateless
        # external ops. The deny entry matches nothing here, so it blocks
        # nothing — it is policy, not behavior.
        deny=["action.execute"],
        ops=ops,
        gates=[Gate("approval", ["approve", "reject"])],
        plans=[Plan("main", steps)],
    )


def test_realistic_pipeline_respects_topo_order_across_effects():
    spec = _pipeline_spec()
    assert check(spec) == []
    model = CannedModel(
        {
            "classify_board": {"top": "Line Cook", "score": 0.85},
            "approve_send": {"ok": True},
            "summarize_batch": {"summary": "1 strong lead"},
        }
    )
    receipt = Executor(
        spec,
        model,
        op_impls={
            "fetch_board": lambda _i: {"board": "test", "n": 1},
            "notify_owner": lambda _i: {"sent": True},
        },
        gate_io=AutoVerdict("approve"),
    ).run()
    assert receipt.status == "completed"
    # Topo order, not listed order — across recorded and external lanes.
    assert [s.var for s in receipt.steps] == [
        "board",
        "top",
        "verdict",
        "summary",
        "notify",
    ]
    gate_step = next(s for s in receipt.steps if s.var == "verdict")
    assert gate_step.gate == "approval" and gate_step.verdict == "approve"
    assert receipt.human_minutes_used == 5


def test_realistic_pipeline_suspends_at_human_gate():
    """Gate-suspend is the closest v0.1 gets to durable execution: the run
    halts with its state recorded instead of proceeding blind. (The IR has
    no durable effect; SUSPEND plus the receipt is the mechanism.)"""
    spec = _pipeline_spec()
    receipt = Executor(
        spec,
        CannedModel({"classify_board": {"top": "Line Cook"}}),
        op_impls={"fetch_board": lambda _i: {"board": "t"}},
        gate_io=SuspendAlways(),
    ).run()
    assert receipt.status == "suspended"
    assert [s.var for s in receipt.steps] == ["board", "top", "verdict"]
    gate_step = receipt.steps[-1]
    assert gate_step.suspended and gate_step.gate == "approval"
    # summarize and notify never ran


def test_depends_on_is_plan_scoped():
    """A step cannot depend on a var from another plan — IR-10."""
    ops = [Op("op_a", effect=Effect.PURE), Op("op_b", effect=Effect.PURE)]
    spec = Spec(
        name="s",
        ops=ops,
        plans=[
            Plan("one", [PlanStep("a", "op_a", [], depends_on=[])]),
            Plan("two", [PlanStep("b", "op_b", ["a"], depends_on=["a"])]),
        ],
    )
    vs = check(spec)
    assert [v.code for v in vs] == ["IR-10"]
    assert "unknown step 'a'" in vs[0].message


def test_when_and_depends_on_round_trip():
    """Canonical form keeps `when` before the trailing depends_on clause."""
    steps = [
        PlanStep("b", "op_b", ["a"], when="a == 'go'", depends_on=["a"]),
        PlanStep("a", "op_a", [], depends_on=[]),
    ]
    ops = [Op("op_a", effect=Effect.PURE), Op("op_b", effect=Effect.PURE)]
    spec = Spec(name="s", ops=ops, plans=[Plan("main", steps)])
    text = dumps(spec)
    assert "when a == 'go' depends_on a" in text
    assert loads(text) == spec
