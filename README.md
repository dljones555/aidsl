<p align="center">
  <br>
  <img src="https://img.shields.io/badge/Work--Surface-IR_v0.1-blue?style=for-the-badge" alt="version">
  <img src="https://img.shields.io/badge/tests-221%20passing-brightgreen?style=for-the-badge" alt="tests">
  <img src="https://img.shields.io/badge/python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="python">
  <br><br>
</p>

<h1 align="center">Work Surface</h1>

<p align="center">
  <strong>Defined work, with receipts.</strong><br>
  You describe the work in plain English. We turn it into a precise definition<br>
  that runs reliably, waits for your people when it should, and proves everything it did.
</p>

---

## The problem

Work is defined nowhere.

The process lives in someone's head, in a chat thread, in tribal knowledge
accumulated over years. When that person leaves, the definition leaves with
them. What remains is folklore: "ask Maria, she knows how the invoice thing
works." Nobody can see the work, price the work, verify the work, or hand
the work to someone — or something — else.

## What this is

Work Surface is a portable work definition. Three layers:

1. **Authoring** — plain English and a small DSL. Replaceable syntax; the
   words change, the meaning doesn't.
2. **The IR** — the portable core. Everything is a **type**, **op**,
   **plan**, **gate**, or **audit rule**. Every op is effect-typed:
   `pure`, `recorded`, `external`, or `suspend`. Steps declare their data
   dependencies with `depends_on`; ordering and concurrency permission fall
   out of the graph. Human judgment enters through **gates** — named, with
   declared verdicts, and the run waits for your people when it should.
3. **Backend adapters** — the IR runs anywhere. The reference executor runs
   it sequentially today; a DAG-capable backend runs the same IR
   concurrently with identical receipts.

And **receipts**: every run produces proof — what ran, what the model said,
what the human decided, what it cost. A non-technical stakeholder can trust
a run by reading the receipt card.

## The IR in ten lines

```
op fetch_boards(query) -> list[posting] effect external
op score_posting(p) -> scored effect recorded
op draft_outreach(s) -> draft effect recorded
op send_outreach(d) -> receipt effect external gate approval

gate approval:
  human decides in [approve, reject]

plan daily_scan:
  postings = fetch_boards(query)
  scored = score_posting(postings) depends_on postings
  drafts = draft_outreach(scored) when scored.score > 0.5 depends_on scored
  sent = send_outreach(drafts) depends_on drafts
```

The model is called only where judgment is needed. Everything else is
declared, checked, and proven. The checker rejects bad definitions before
they run — unknown dependencies, cycles, gateless external calls. A skipped
step cascades: no data, no run, and the receipt says why.

## Status

The IR v0.1 core is built and green: checker, reference executor, canonical
text form with round-trip parsing, human gates with suspend, audit rules,
and receipt cards. 221 tests.

- PR #8 — IR first cut: the five primitives, effect types, gates, receipts
- PR #9 — `depends_on`: the DAG, cycle detection, cascade-skip semantics
- PR #10 — receipt card: the user-presentable proof of a run

Next: the opportunity matcher — our own daily pipeline, re-expressed as
defined work. Customer zero.

## The authoring layer

The v0.1 `.ai` DSL (EXTRACT, CLASSIFY, DRAFT over typed schemas) still works —
it is now one authoring skin over the IR, not the product. The product is the
portable definition.

## Who's building this

David Jones — product vision and language design.

Muse Bot has joined the engineering and product team — an AI teammate
running specs, tests, and reviews. One story per branch, nothing to main
without David.

## Quick start

```bash
git clone https://github.com/dljones555/aidsl.git
cd aidsl && uv sync
uv run pytest -q          # 221 tests
uv run ruff check .       # lint
```

## License

Business Source License 1.1 — free for non-production use. Commercial or
production use requires a license. See [LICENSE](LICENSE) for full terms.

Interested in defining work with us — as a design partner or collaborator?
Reach out to [dljones555](https://github.com/dljones555).
