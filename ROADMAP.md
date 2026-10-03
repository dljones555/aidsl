# Work Surface Roadmap

One person, one AI teammate. No funding. The goal is simple:

**One customer, or kibosh.** A real operator saying "build this for me" on a
small-stakes slice — or we stop.

## Shipped

- **PR #8** — IR v0.1 first cut: the five primitives (type, op, plan, gate,
  audit rule), effect types (pure / recorded / external / suspend), human
  gates, receipts, canonical text form. 193 tests.
- **PR #9** — `depends_on`: per-step data dependencies, the DAG, cycle
  detection (IR-10 / IR-11), topo-order executor, cascade-skip semantics.
- **PR #10** — receipt card: the user-presentable proof of a run —
  what ran, what the model said, what the human decided, what it cost.

Main is green: 221 tests. Nothing merges without David.

## Now: the vertical slice (PBI #38)

The opportunity matcher as customer zero — our own daily pipeline,
re-expressed as defined work:

1. Interview captures the matching criteria.
2. Criteria lower to DSL, then IR.
3. The matcher runs with declared effects.
4. David approves leads at a human gate.
5. Receipts carry source provenance, decisions, and costs.

It needs nobody's permission. It is the demo and the dogfood.

## The bigger vision: the authoring pipeline

Nobody hand-rolls IR. People describe work the way people talk, and the
pipeline carries it down to the portable definition:

**Interview → English → Skills → DSL → IR** — and eventually a generated
designer.

- **Interview** — the FDE-in-a-box: plain questions that draw the work out
  of the people who do it.
- **English** — the draft definition in readable prose, corrected in words
  before it ever becomes code.
- **Skills** — agent skills that write the DSL: plain English in, DSL out.
- **DSL** — the human-owned surface. Readable, diffable, version-controlled.
  Definitely in; we don't erase it.
- **IR** — the portable contract: type, op, plan, gate, audit rule.
- **Designer (generated, later)** — the visual surface, generated from the
  definition, not drawn by hand.

Every surface is a projection of the definition below it.

## Next (proposed order)

1. **#6 — Settle `approve`.** Own verb or assert-in-the-human-lane? A
   decision first; everything about gates hangs off it.
2. **#5 — Assert language.** Input-side contracts: the dual of gates.
   Gates check outputs and approvals; asserts check inputs and provenance.
3. **#14 — Partial failure and retry.** Per-op failure policy
   (retry / fallback / escalation / stop). Required before any real
   customer run.
4. **Cost cluster (#8 + #13 + #15, merged).** One PBI: compile-time cost
   estimation, the per-run token/labor ledger, and declared budgets the
   executor refuses to exceed.
5. **#20 + #21 — Micro-interview and plain-language review.** A few
   questions produce a draft definition; the draft renders back in readable
   form for correction before it runs. The FDE wedge.
6. **#1 — Publish the Layer 2 IR spec.** Written so a stranger can
   implement a conforming checker without reading our code.

## Merged (duplicates folded)

- #8 + #13 + #15 → one cost-model PBI (estimation + ledger + guardrails).
- #20 + #26 → one interview/wizard PBI. The high-touch (#25) vs
  self-serve (#26) tension stays open until a customer picks.
- #4 + #5 + #6 → one policy/approvals cluster; #6 decides first.

## Deferred

- #47 — Python-authored plans lowering to IR. Future wedge, not now.
- #48 — Agent SDK primitive survey. Spike, not now.
- Parked repo chores (TASKS.md): untouched until customers ask.

## Tensions (David's call)

- **Layer 1 vs Layer 2.** The repo DSL stays stable; new semantics land in
  the IR, not in new verbs.
- **#6.** `approve` as its own verb vs assert-in-the-human-lane.
- **#25 vs #26.** High-touch "three conversations, one map" vs the
  self-serve wizard. Keep both until a customer picks.

## Not doing

- No new PBIs. Consolidate first; net zero.
- No paid APIs, cloud, or spend without approval.
- One story per branch. Checkpoint = demo + diff + three decision gates max.

---

*Raw backlog: 49 PBIs harvested 2026-09-30 (working copy, not in this repo).
Triaged 2026-10-03. David prioritizes; this file proposes.*
