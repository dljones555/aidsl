# Eval: does the IR pipeline match the known-good shortlist?

The harness the whole PBI #38 program is measured against.

## Run it

```bash
python3 examples/eval_opmatcher.py                  # default fixture
python3 examples/eval_opmatcher.py --fixture PATH   # your own fixture
```

Exit 0 on exact shortlist equality, 1 on any mismatch — CI-usable.
Output is one line per posting plus a summary score:

```
[PASS] p01 Busser: expected surface, surfaced — restaurant/busser is a favored category; ...
...
10/10 correct
```

## What "match" means

Exact shortlist equality on the fixture: every posting the fixture marks
`_expect: surface` must get a draft from the pipeline, AND no posting
marked `_expect: skip` may get one. One wrong posting fails the eval.

## The fixture

`examples/ir/eval_postings.jsonl` — one posting per line. Each line carries:

- the posting itself: `id` (unique), `title`, `employer`, `city`, `pay`, `url`
- `_judge`: the classifier's judgment — `{"score": 0.0-1.0, "excluded": bool}`
- `_expect`: `"surface"` or `"skip"` — the known-good answer
- `_why`: one line saying why, in terms of the real matching criteria

The real criteria (from the daily scan): daily-pay roles in Huntington
Beach, Fountain Valley, Costa Mesa, Newport Beach, Santa Ana. EXCLUDE
driving, mechanical/auto, personal care/caregiver, marketing/ad roles.
A posting matches only with a plausible daily-pay signal. The fixture
covers the edges: excluded-category-with-daily-pay (p02, p07, p09),
in-city-without-daily-pay (p03, p10), out-of-city-with-daily-pay (p04),
and clear matches (p01, p05, p06, p08).

## Extend it

Add a JSONL line with a unique `id`, a `_judge`, an `_expect`, and a
`_why`. Keep the `_why` honest — it is the ground truth the future live
model will be measured against. The eval auto-sizes: draft canned
responses are generated one per posting, so no other file changes.

## Scope honesty

Today the canned judgments are fixed, so this eval measures the
pipeline machinery: fan-out, the spec's `when`-filter, ordering. The
fixture's `_expect` annotations are cross-checked against the spec's
real `when` expression (see `test_fixture_expectations_agree_with_spec_when_rule`),
so a misbuilt fixture fails loudly.

When live model wiring lands, the same fixture and expected shortlist
measure the model's judgments instead — that is the point of the
harness. The day the eval passes with a live model, the IR pipeline
matches Muse's own scan output.
