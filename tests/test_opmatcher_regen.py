"""Regeneration exam: the English spec is the source of truth.

PBI #38, stories 3-4. These tests prove the full honest chain:

    English -> DSL text -> parse (ir.loads) -> check -> Spec

No Python objects cross the seam: the committed .dsl file is deleted and
regenerated from the English spec, and only the parser's output is ever
compared. They also prove the English is load-bearing — a parameter
change must change the DSL, while prose rewording must not.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from examples.gen_from_english import generate_dsl_text, load_dsl
from ir import check, dumps, loads

ENGLISH_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.english.md"
DSL_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.dsl"
REFERENCE_PATH = ROOT / "examples" / "ir" / "opportunity_pipeline.ir"


@pytest.fixture()
def english_text() -> str:
    """The committed English spec, as text."""
    return ENGLISH_PATH.read_text()


def test_dsl_regeneration_matches_reference(english_text: str):
    """Regenerated DSL text is byte-identical to the committed pipeline."""
    assert generate_dsl_text(english_text) == REFERENCE_PATH.read_text()


def test_committed_dsl_matches_regeneration(english_text: str):
    """The delete-and-regenerate test: the committed .dsl file is exactly
    what the English spec produces. Delete it, re-run, no difference."""
    assert DSL_PATH.read_text() == generate_dsl_text(english_text)


def test_dsl_goes_through_the_parser(english_text: str):
    """Nothing bypasses the parser: the DSL text is consumed only via
    ir.loads, and the parsed spec carries the pipeline's structure."""
    spec = load_dsl(generate_dsl_text(english_text))
    assert [p.name for p in spec.plans] == ["daily_scan"]
    assert [o.name for o in spec.ops] == [
        "fetch_boards",
        "classify_posting",
        "draft_outreach",
        "send_outreach",
    ]
    assert [g.name for g in spec.gates] == ["approval"]
    assert spec.ops[-1].gate == "approval"  # the gate survived the text


def test_regenerated_spec_checks_clean(english_text: str):
    """The parsed definition passes the checker with zero violations."""
    assert check(load_dsl(generate_dsl_text(english_text))) == []


def test_regenerated_dsl_round_trips(english_text: str):
    """Canonical form is stable: parse the DSL text, dump again, no change."""
    once = generate_dsl_text(english_text)
    assert dumps(loads(once)) == once


def test_mutated_threshold_changes_dsl(english_text: str):
    """Editing a declared parameter MUST change the generated DSL.

    This is the proof the English spec is load-bearing: David raises the
    bar from 0.7 to 0.8 and the pipeline definition changes with it.
    """
    mutated = english_text.replace("score_threshold: 0.7", "score_threshold: 0.8")
    assert mutated != english_text  # the edit actually landed
    regen = generate_dsl_text(mutated)
    assert regen != REFERENCE_PATH.read_text()
    assert "s.score > 0.8 and not s.excluded" in regen
    assert check(load_dsl(regen)) == []  # still a valid definition


def test_missing_cities_fails_loudly(english_text: str):
    """Dropping a required contract line fails instead of silently drifting."""
    lines = [
        ln for ln in english_text.splitlines() if not ln.strip().startswith("cities:")
    ]
    with pytest.raises(ValueError, match="missing required parameters"):
        generate_dsl_text("\n".join(lines))


def test_prose_edits_dont_change_dsl(english_text: str):
    """Rewording the human prose must never change the generated definition."""
    reworded = english_text.replace(
        "find the ones worth\nDavid's time: daily-pay roles he could actually take.",
        "surface the daily-pay roles actually worth David's morning.",
    )
    assert reworded != english_text  # the edit actually landed
    assert generate_dsl_text(reworded) == REFERENCE_PATH.read_text()
