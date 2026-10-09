# Opportunity Matcher — English spec

This file is the source of truth for the daily opportunity scan. If
anything described below changes, the pipeline definition is regenerated
from this file — never edited by hand.

## What it does

Every morning, fetch today's job postings, score each one for fit, and
show the shortlist: the postings worth David's time. It's a list —
nothing is drafted, nothing is sent, no approval step.

## Where it looks

Job boards, read from the postings file. Only these cities count:
Huntington Beach, Fountain Valley, Costa Mesa, Newport Beach, Santa Ana.
Anywhere else is out, no matter how good the posting looks.

## What counts as a match

A posting is worth surfacing only if it plausibly pays daily. A stated
daily-pay program ("work today, get paid tomorrow", DailyPay, and the
like) counts, and so does clear daily cash pay.

These categories are never a match, even with daily pay attached:
driving, mechanical/auto work, personal care or caregiving, marketing
or advertising roles.

These are the kinds of work to favor: restaurant (server, busser, prep),
grocery, stocking, packing, light setup and teardown, customer service,
tech skills, event work.

## How it decides

Each posting is scored for fit from 0 to 1. The shortlist shows postings
scoring above 0.7 that aren't in an excluded category. The run records
every scoring, not just the shortlist.

## Machine-readable parameters

The block below is read by the generator (examples/gen_from_english.py).
It is the contract: every line is required, and changing a value changes
the generated pipeline. In production, an inference step reads the prose
above; in this spike, a deterministic reader reads the block below — the
round-trip mechanics are identical. Rewording the prose must never change
the generated definition; editing this block must.

```spec-params
goal: rank today's postings so David sees the 5 worth his time by 9:15am
author: david@local
cities: Huntington Beach, Fountain Valley, Costa Mesa, Newport Beach, Santa Ana
excluded_categories: driving, mechanical/auto, personal care/caregiver, marketing/advertising
favored_categories: restaurant, grocery, stocking, packing, setup/teardown, customer service, tech skills, event work
daily_pay_required: true
score_threshold: 0.7
classify_prompt: job_fit_v1
postings_source: examples/ir/postings.jsonl
```
