"""Regenerate the opportunity matcher DSL from its English spec.

PBI #38, story 4. Fixes story 3's shortcut: the generator now emits a real
DSL TEXT artifact (examples/ir/opportunity_matcher.dsl), and everything
downstream consumes it through the real parser (ir.loads). The chain is:

    English -> DSL text -> parse -> check -> Spec

No Python objects cross the seam. Delete the .dsl file, re-run, and the
pipeline comes back byte-identical.

SEAM CHOICE (documented; David's call to change): the DSL surface used
here is the canonical IR text form, parsed by ir.loads. The v0.1 .ai DSL
(lowered by ir/lower.py) cannot express this pipeline, so emitting .ai
would silently drop the approval gate. The canonical text form is a real
DSL: specified, human-readable and writable, with a real parser and a
round-trip printer.

DSL GAP vs the v0.1 .ai DSL — what lower_program cannot carry:
- gates: .ai has no REVIEW/HITL verb, so `gate approval` on
  send_outreach would be lost. This alone disqualifies .ai here.
- step-level when: `d = draft_outreach(s) when s.score > 0.7 ...` —
  FLAG WHEN lowers to audit rules, not step conditions.
- budgets: `budget tokens 10000 human_minutes 15` — SET is binding
  config and deliberately dropped; no budget syntax exists.
- deny lists: `deny: action.execute` — no .ai concept.
- suspend-action audits: `audit budget_tokens: ... -> suspend` —
  FLAG WHEN only produces action "flag".
- kv:// knowledge: FROM produces fs:// entries only.
.ai CAN carry: types (DEFINE), sources (FROM), model ops with prompts
(EXTRACT/CLASSIFY/DRAFT), flag rules, the output sink.

PROPOSAL (needs David's decision):
- Option A: extend the .ai grammar (GATE verb or gate clause, step-level
  WHEN, BUDGET block, DENY). Real language-design work; makes .ai the
  full-fidelity authoring language.
- Option B (recommended): declare the canonical text form the DSL for IR
  authoring — already specified, writable, parsed and printed round-trip —
  and keep .ai as the narrower skin for simple extract/classify/draft
  pipelines. No grammar work, no information loss.

HONESTY NOTE — what this proves and what it does not:

Proves:
- The full chain is real text: a single English source regenerates a
  committed DSL file, which the parser — not Python objects — turns
  into the checked IR. Delete the .dsl, re-run, byte-identical.
- The English spec is load-bearing: editing a declared parameter (e.g.
  the score threshold) changes the DSL and the IR; rewording the prose
  does not. The contract is enforced, not decorative.
- Everything below the English is mechanical: render text, parse,
  check. No judgment lives in the generator.

Does NOT prove:
- That an LLM drafts a correct DSL from English prose. That is the real
  inference step and it needs live-model work with spend approval
  (queued as a follow-up). Here a deterministic reader parses the
  machine-readable ```spec-params``` block that the English file carries
  alongside its prose; the round-trip mechanics are identical.
- That classifier policy (cities, excluded/favored categories) is fully
  expressed in the IR. Those criteria are validated as present — the
  English spec is invalid without them — but today they ride with the
  classifier prompt/policy the ``classify_posting`` op names, not as IR
  structure. Threading policy into the IR is future work.

Usage:
    python3 examples/gen_from_english.py [--out PATH] [--english PATH]
    # regenerates examples/ir/opportunity_matcher.dsl in place by default
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ir import Spec, check, loads

ENGLISH_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.english.md"
DSL_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.dsl"

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


def render_dsl(p: dict[str, str]) -> str:
    """Render the DSL text (canonical form) from validated parameters.

    This is the inference stand-in's output: TEXT, exactly as a production
    LLM would emit. Nothing downstream may use anything but this text —
    the parser (ir.loads) is the only way in.
    """
    threshold = p["score_threshold"]
    tokens = p["token_budget"]
    human_minutes = p["human_minutes_budget"]
    gate = p["gate_name"]
    verdicts = ", ".join(v.strip() for v in p["gate_verdicts"].split(","))
    lines = [
        "spec opportunity_pipeline@v1",
        "  parent none",
        f'  author "{p["author"]}"',
        f'  goal "{p["goal"]}"',
        f"  budget tokens {tokens} human_minutes {human_minutes}",
        "",
        "knowledge:",
        f'  boards @ "{p["postings_source"]}"',
        f'  exclusion_rules @ "{p["exclusion_rules"]}"',
        "",
        "effects: model.complete, human.review",
        "deny: action.execute",
        "",
        "type posting = { title: text, pay: text, employer: text, url: text }",
        (
            "type scored = { title: text, pay: text, employer: text, url: text,"
            " score: float, excluded: bool }"
        ),
        "type draft = { to: text, subject: text, body: text }",
        "",
        "op fetch_boards() -> posting[] effect recorded cap fs.read",
        (
            "op classify_posting(posting) -> scored effect external"
            f' cap model.complete using prompt "{p["classify_prompt"]}"'
        ),
        (
            "op draft_outreach(scored) -> draft effect external"
            f' cap model.complete using prompt "{p["outreach_prompt"]}"'
        ),
        (
            "op send_outreach(draft) -> receipt effect external"
            f" cap action.execute gate {gate}"
        ),
        "",
        f"gate {gate}:",
        f"  human decides in [{verdicts}]",
        "",
        f"audit budget_tokens: tokens_used <= {tokens} -> suspend",
        "",
        "plan daily_scan:",
        "  p = fetch_boards()",
        "  s = classify_posting(p)",
        f"  d = draft_outreach(s) when s.score > {threshold} and not s.excluded",
        "  r = send_outreach(d)",
        "",
    ]
    return "\n".join(lines)


def generate_dsl_text(english_text: str) -> str:
    """English spec in, DSL text out. The text is the artifact."""
    return render_dsl(read_params(english_text))


def load_dsl(dsl_text: str) -> Spec:
    """The parse seam: DSL text -> Spec, checker enforced. Fails loudly."""
    spec = loads(dsl_text)
    violations = check(spec)
    if violations:
        raise ValueError(
            "DSL text failed the checker: "
            + "; ".join(f"{v.code} {v.message}" for v in violations)
        )
    return spec


def main() -> None:
    """Regenerate the committed DSL file from the English spec."""
    parser = argparse.ArgumentParser(
        description="Regenerate opportunity_matcher.dsl from its English spec."
    )
    parser.add_argument(
        "--out", default=str(DSL_PATH), help="where to write the DSL text"
    )
    parser.add_argument(
        "--english", default=str(ENGLISH_PATH), help="English spec to read"
    )
    args = parser.parse_args()
    dsl_text = generate_dsl_text(Path(args.english).read_text())
    load_dsl(dsl_text)  # the parser is the gate: invalid text never lands
    Path(args.out).write_text(dsl_text)
    print(f"wrote {args.out} ({len(dsl_text)} chars, checker clean)")


if __name__ == "__main__":
    main()
