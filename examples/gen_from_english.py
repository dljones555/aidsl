"""Regenerate the opportunity matcher DSL from its English spec.

PBI #38, story 4 (revised 2026-10-08, David's direction). The .dsl is
gone — it was an unspecified invention, neither .ai nor .ir. The chain:

    English -> .ai text -> parse (aidsl.parser) -> lower (ir.lower_program)
      -> check -> Spec -> .ir text

No Python objects cross the seam. Delete the .ai file, re-run, and both
artifacts come back byte-identical. There is no gate: the pipeline is a
list (fetch postings, score each, show the shortlist).

HONESTY NOTE — what this proves and what it does not:

Proves:
- The full chain is real text: a single English source regenerates a
  committed .ai file; the real .ai parser (not Python objects) plus the
  real lowering turn it into the checked IR. Delete the .ai, re-run,
  byte-identical.
- The English spec is load-bearing: editing a declared parameter (e.g.
  the score threshold) changes the .ai; rewording the prose does not.
- Everything below the English is mechanical: render text, parse,
  lower, check. No judgment lives in the generator.

Does NOT prove:
- That an LLM drafts a correct .ai from English prose. A deterministic
  reader parses the machine-readable ```spec-params``` block; the
  round-trip mechanics are identical.
- That classifier policy (cities, excluded/favored categories,
  daily-pay rule, score threshold) is expressed in the IR. Those are
  validated present — the English spec is invalid without them — but
  they ride with the classifier prompt, not as IR structure. The
  threshold is rendered as a comment in the .ai so the artifact still
  changes when the contract changes.
- The shortlist filter (score > threshold, not excluded) is host
  presentation policy, applied by the write_output implementation. The
  definition scores every posting and records everything; the list
  shows the fits. The threshold's single source of truth is the English
  spec-params, read via read_params.

Usage:
    python3 examples/gen_from_english.py [--ai PATH] [--ir PATH]
                                         [--english PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aidsl.parser import parse
from ir import Spec, check, dumps, lower_program

ENGLISH_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.english.md"
AI_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.ai"
IR_PATH = ROOT / "examples" / "ir" / "opportunity_pipeline.ir"

# Every key the contract requires. The IR-consuming subset is the source,
# prompt, and goal; the classifier-policy subset (cities, categories,
# daily-pay rule, threshold) is validated for presence — the English spec
# is invalid without it — even though the IR has no slot for it (see
# honesty note).
REQUIRED_KEYS = [
    "goal",
    "author",
    "cities",
    "excluded_categories",
    "favored_categories",
    "daily_pay_required",
    "score_threshold",
    "classify_prompt",
    "postings_source",
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


def render_ai(p: dict[str, str]) -> str:
    """Render the .ai DSL text (v0.1 syntax) from validated parameters.

    This is the inference stand-in's output: TEXT, exactly as a production
    LLM would emit. Nothing downstream may use anything but this text —
    the .ai parser is the only way in.
    """
    lines = [
        "-- Opportunity matcher: daily scan to a ranked shortlist.",
        "-- No gate: a list. Nothing is drafted, nothing is sent.",
        "-- Generated from opportunity_matcher.english.md — do not hand-edit.",
        (
            "-- Classifier policy "
            f"(score_threshold {p['score_threshold']}, cities, categories,"
        ),
        "-- daily-pay rule) rides with the classifier prompt; the English",
        "-- spec-params are the contract. The shortlist filter",
        f"-- (score > {p['score_threshold']}, not excluded) is host",
        "-- presentation policy on the write_output step.",
        "",
        "DEFINE posting:",
        "  title    TEXT",
        "  pay      TEXT",
        "  employer TEXT",
        "  url      TEXT",
        "",
        "DEFINE scored:",
        "  title    TEXT",
        "  pay      TEXT",
        "  employer TEXT",
        "  url      TEXT",
        "  score    NUMBER",
        "  excluded YES/NO",
        "",
        f"FROM {p['postings_source']}",
        f"EXTRACT scored PROMPT {p['classify_prompt']}",
        "OUTPUT shortlist.json",
        "",
    ]
    return "\n".join(lines)


def generate_ai_text(english_text: str) -> str:
    """English spec in, .ai text out. The text is the artifact."""
    return render_ai(read_params(english_text))


def load_ai(ai_path: Path) -> Spec:
    """The parse seam: .ai file -> parse -> lower -> check -> Spec.

    Fails loudly on parse errors, lowering problems, or checker
    violations. Nothing downstream may construct the Spec by hand.
    """
    program = parse(str(ai_path))
    spec = lower_program(program, name="opportunity_pipeline", version="v1")
    # SAFETY SCOPE (documented; David's language-design call): the .ai v0.1
    # grammar has no deny syntax, but IR-04 requires every gateless
    # external op to sit under a deny list. A list pipeline may never
    # execute actions, so the generator applies the standing scope
    # "deny: action.execute" here, in the open. If .ai grows deny syntax,
    # this moves into the text.
    spec.deny = ["action.execute"]
    violations = check(spec)
    if violations:
        raise ValueError(
            "lowered spec failed the checker: "
            + "; ".join(f"{v.code} {v.message}" for v in violations)
        )
    return spec


def generate_ir_text(ai_text: str) -> str:
    """Lower .ai text all the way to .ir text.

    Goes through a temp file because aidsl.parser.parse takes a path —
    the parse still goes through the real parser; nothing is built by
    hand on the way through.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".ai", delete=False) as tmp:
        tmp.write(ai_text)
        tmp_path = Path(tmp.name)
    try:
        return dumps(load_ai(tmp_path))
    finally:
        tmp_path.unlink()


def main() -> None:
    """Regenerate the committed .ai and .ir from the English spec."""
    parser = argparse.ArgumentParser(
        description="Regenerate opportunity_matcher.ai/.ir from English."
    )
    parser.add_argument(
        "--ai", default=str(AI_PATH), help="where to write the .ai text"
    )
    parser.add_argument(
        "--ir", default=str(IR_PATH), help="where to write the .ir text"
    )
    parser.add_argument(
        "--english", default=str(ENGLISH_PATH), help="English spec to read"
    )
    args = parser.parse_args()
    english_text = Path(args.english).read_text()
    ai_text = generate_ai_text(english_text)
    ai_path = Path(args.ai)
    ai_path.write_text(ai_text)
    load_ai(ai_path)  # the parser+lowering are the gate: invalid text never lands
    ir_text = generate_ir_text(ai_text)
    Path(args.ir).write_text(ir_text)
    print(f"wrote {args.ai} and {args.ir} (checker clean)")


if __name__ == "__main__":
    main()
