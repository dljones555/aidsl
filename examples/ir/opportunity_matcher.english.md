# Opportunity Matcher — English spec

This file is the source of truth for the daily opportunity scan. If
anything described below changes, the pipeline definition is regenerated
from this file — never edited by hand.

## What it does

Every morning, check the job boards and show me the shortlist: the
daily-pay jobs worth my time. Just a list — nothing drafted, nothing sent.

## Where it looks

Huntington Beach, Fountain Valley, Costa Mesa, Newport Beach, Santa Ana.
Anywhere else is out, no matter how good the posting looks.

## What counts as a match

It's got to plausibly pay daily — a daily-pay program ("work today, get
paid tomorrow" and the like), or clear daily cash.

Never a match, even with daily pay: driving, mechanical/auto work,
personal care or caregiving, marketing or advertising roles.

The kinds of work I like: restaurant (server, busser, prep), grocery,
stocking, packing, light setup and teardown, customer service, tech
skills, event work.

## How it decides

Score each posting 0 to 1 for fit. Show me the ones above 0.7 that aren't
excluded. Record every scoring, not just the shortlist.

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
