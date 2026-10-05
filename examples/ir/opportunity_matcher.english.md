# Opportunity Matcher — English spec

This file is the source of truth for the daily opportunity scan. If
anything described below changes, the pipeline definition is regenerated
from this file — never edited by hand.

## What it does

Every morning, fetch today's job postings and find the ones worth
David's time: daily-pay roles he could actually take. The scan ranks
postings, drafts outreach for the good ones, and waits for David to
approve before anything is sent.

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

Each posting is scored for fit from 0 to 1. Anything scoring above 0.7
that isn't in an excluded category gets an outreach draft. The rest are
dropped quietly — no draft, no send.

## The human gate

Nothing is sent without David. He reviews the drafts and decides per
run: approve, edit, or reject. A rejection drops the send; the run still
records what happened.

## Budgets

A run may spend at most 10000 tokens and 15 minutes of human time. If the
token budget would be exceeded, the run suspends instead of spending more.

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
outreach_prompt: outreach_v1
postings_source: fs://examples/ir/postings.jsonl
exclusion_rules: kv://exclusion-rules
gate_name: approval
gate_verdicts: approve, edit, reject
token_budget: 10000
human_minutes_budget: 15
```
