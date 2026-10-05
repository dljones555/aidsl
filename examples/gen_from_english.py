"""Regenerate the opportunity matcher IR from its English spec.

PBI #38, story 3 (spike). The English file
(examples/ir/opportunity_matcher.english.md) is the source of truth;
this script is the deterministic stand-in for the inference step that,
in production, reads the prose and drafts the definition.

HONESTY NOTE — what this spike proves and what it does not:

Proves:
- Round-trip mechanics: a single English source file regenerates the
  pipeline definition deterministically. Delete the generated artifact,
  re-run, byte-identical IR.
- The English spec is load-bearing: editing a declared parameter (e.g.
  the score threshold) changes the generated IR; rewording the prose
  does not. The contract is enforced, not decorative.
- Everything below the English is mechanical: parse, check, emit. No
  judgment lives in the generator.

Does NOT prove:
- That an LLM drafts a correct definition from English prose. That is
  the real inference step and it needs live-model work with spend
  approval (queued as a follow-up). Here a deterministic reader parses
  the machine-readable ````spec-params```` block that the English file
  carries alongside its prose.
- That classifier policy (cities, excluded/favored categories) is fully
  expressed in the IR. Those criteria are validated as present — the
  generator fails loudly without them — but today they ride with the
  classifier prompt/policy the ``classify_posting`` op names, not as IR
  structure. Threading policy into the IR is future work.

Usage:
    python3 examples/gen_from_english.py [--out PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ir import (
    AuditRule,
    Effect,
    Field,
    Gate,
    Knowledge,
    Op,
    Plan,
    PlanStep,
    Spec,
    TypeDef,
    check,
    dumps,
)

ENGLISH_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.english.md"

# Every key the contract requires. The IR-consuming subset is marked
# below; the classifier-policy subset (cities, categories, daily-pay
# rule) is validated for presence — the English spec is invalid without
# it — even though the IR has no slot for it yet (see honesty note).
REQUIRED_KEYS = [
    "goal",
    "author",
    "cities",
    "excluded_categories",
    "favored_categories",
    "daily_pay_required",
    "score_threshold",
    "classify_prompt",
    "outreach_prompt",
    "postings_source",
    "exclusion_rules",
    "gate_name",
    "gate_verdicts",
    "token_budget",
    "human_minutes_budget",
]

# Declared capabilities of this pipeline (structural, not per-run policy).
EFFECTS = ["model.complete", "human.review"]
DENY = ["action.execute"]


def read_params(english_text: str) -> dict[str, str]:
    """Extract the ````spec-params```` block; fail loudly if it is absent."""
    m = re.search(r"```spec-params\n(.*?)```", english_text, re.DOTALL)
    if not m:
        raise ValueError("English spec has no ```spec-params block")
    params: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        params[key.strip()] = value.strip()
    missing = [k for k in REQUIRED_KEYS if k not in params]
    if missing:
        raise ValueError(
            "English spec is missing required parameters: " + ", ".join(missing)
        )
    return params


def build_spec(p: dict[str, str]) -> Spec:
    """Build the pipeline Spec from validated English parameters."""
    threshold = p["score_threshold"]
    tokens = int(p["token_budget"])
    human_minutes = int(p["human_minutes_budget"])
    gate = p["gate_name"]
    return Spec(
        name="opportunity_pipeline",
        version="v1",
        parent="none",
        author=p["author"],
        goal=p["goal"],
        budget_tokens=tokens,
        budget_human_minutes=human_minutes,
        knowledge=[
            Knowledge(name="boards", uri=p["postings_source"]),
            Knowledge(name="exclusion_rules", uri=p["exclusion_rules"]),
        ],
        effects=list(EFFECTS),
        deny=list(DENY),
        types=[
            TypeDef(
                name="posting",
                fields=[
                    Field(name="title", type="text"),
                    Field(name="pay", type="text"),
                    Field(name="employer", type="text"),
                    Field(name="url", type="text"),
                ],
            ),
            TypeDef(
                name="scored",
                fields=[
                    Field(name="title", type="text"),
                    Field(name="pay", type="text"),
                    Field(name="employer", type="text"),
                    Field(name="url", type="text"),
                    Field(name="score", type="float"),
                    Field(name="excluded", type="bool"),
                ],
            ),
            TypeDef(
                name="draft",
                fields=[
                    Field(name="to", type="text"),
                    Field(name="subject", type="text"),
                    Field(name="body", type="text"),
                ],
            ),
        ],
        ops=[
            Op(
                name="fetch_boards",
                params=[],
                returns="posting[]",
                effect=Effect.RECORDED,
                capability="fs.read",
            ),
            Op(
                name="classify_posting",
                params=["posting"],
                returns="scored",
                effect=Effect.EXTERNAL,
                capability="model.complete",
                using=p["classify_prompt"],
                using_kind="prompt",
            ),
            Op(
                name="draft_outreach",
                params=["scored"],
                returns="draft",
                effect=Effect.EXTERNAL,
                capability="model.complete",
                using=p["outreach_prompt"],
                using_kind="prompt",
            ),
            Op(
                name="send_outreach",
                params=["draft"],
                returns="receipt",
                effect=Effect.EXTERNAL,
                capability="action.execute",
                gate=gate,
            ),
        ],
        gates=[
            Gate(name=gate, verdicts=[v.strip() for v in p["gate_verdicts"].split(",")])
        ],
        audits=[
            AuditRule(
                name="budget_tokens",
                expr=f"tokens_used <= {tokens}",
                action="suspend",
            )
        ],
        plans=[
            Plan(
                name="daily_scan",
                steps=[
                    PlanStep(var="p", op="fetch_boards", args=[]),
                    PlanStep(var="s", op="classify_posting", args=["p"]),
                    PlanStep(
                        var="d",
                        op="draft_outreach",
                        args=["s"],
                        when=f"s.score > {threshold} and not s.excluded",
                    ),
                    PlanStep(var="r", op="send_outreach", args=["d"]),
                ],
            )
        ],
    )


def generate_ir_text(english_text: str) -> str:
    """English spec in, canonical IR text out. Fails loudly on violations."""
    spec = build_spec(read_params(english_text))
    violations = check(spec)
    if violations:
        raise ValueError(
            "generated spec failed the checker: "
            + "; ".join(f"{v.code} {v.message}" for v in violations)
        )
    return dumps(spec)


def main() -> None:
    """Regenerate the IR from the English spec; print or write it."""
    parser = argparse.ArgumentParser(
        description="Regenerate opportunity_pipeline.ir from its English spec."
    )
    parser.add_argument("--out", help="write IR text here instead of stdout")
    parser.add_argument(
        "--english", default=str(ENGLISH_PATH), help="English spec to read"
    )
    args = parser.parse_args()
    text = generate_ir_text(Path(args.english).read_text())
    if args.out:
        Path(args.out).write_text(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
