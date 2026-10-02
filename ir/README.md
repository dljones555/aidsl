# Work Surface IR — Layer 2 (v0.1 first cut)

The durable contract. Everything is a **type, op, plan, gate, or audit
rule**. Each op is effect-typed — **pure / recorded / external /
suspend** — the human-CPU-GPU triad as effect classes with different
latency/cost profiles.

The `.ai` DSL (Layer 1, the authoring skin) compiles **down** to this.
Swap the skin; the IR stands.

## Files

- `model.py` — dataclasses + the canonical text form (`dumps`/`loads`).
  The printed `.ir` file is the customer-owned artifact.
- `eval.py` — tiny safe expression evaluator for `when` clauses and
  audit predicates (no `eval()`).
- `lower.py` — the lowering table: DSL → IR. `SET` (model, temperature,
  seed) is binding config and is deliberately dropped — changing the
  model must not change the definition.
- `check.py` — right-sized verification. Deterministic, no model calls.
  A spec that fails `check()` should not run.
- `exec.py` — the executor. It executes the contract; models and humans
  are temp workers it hires. Produces a `RunReceipt`.
- `stub.py` — the model inference API. `CannedModel` for tests,
  `FileModel` for **super-muse mode**: a human plays the model by
  writing a JSONL responses file. The executor is real, the
  determinism is real, and the only nondeterminism in the building is
  the human in the suit.

## Demo

`examples/ir/opportunity_pipeline.ir` — the daily job scan, lowered to
canonical IR and run end to end. `deny: action.execute` keeps it in
shadow mode: drafts are real, sends cannot run yet.

DBOS is the next lowering target (durable plans, checkpointed steps);
the spec does not change when the target does.
