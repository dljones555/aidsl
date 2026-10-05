"""Regeneration exam: the English spec is the source of truth.

PBI #38, story 3 (spike). These tests prove the round-trip mechanics:
delete the generated artifact, regenerate from the English spec, and the
IR is byte-identical. They also prove the English is load-bearing — a
parameter change must change the IR, while prose rewording must not.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from examples.gen_from_english import generate_ir_text
from ir import check, dumps, loads

ENGLISH_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.english.md"
REFERENCE_PATH = ROOT / "examples" / "ir" / "opportunity_pipeline.ir"


@pytest.fixture()
def english_text() -> str:
    """The committed English spec, as text."""
    return ENGLISH_PATH.read_text()


def test_regeneration_matches_reference(english_text: str):
    """Regenerated IR is byte-identical to the committed pipeline spec."""
    assert generate_ir_text(english_text) == REFERENCE_PATH.read_text()


def test_regenerated_spec_checks_clean(english_text: str):
    """The regenerated definition passes the checker with zero violations."""
    assert check(loads(generate_ir_text(english_text))) == []


def test_regenerated_spec_round_trips(english_text: str):
    """Canonical form is stable: parse the output, dump again, no change."""
    once = generate_ir_text(english_text)
    assert dumps(loads(once)) == once


def test_mutated_threshold_changes_ir(english_text: str):
    """Editing a declared parameter MUST change the generated IR.

    This is the proof the English spec is load-bearing: David raises the
    bar from 0.7 to 0.8 and the pipeline definition changes with it.
    """
    mutated = english_text.replace("score_threshold: 0.7", "score_threshold: 0.8")
    assert mutated != english_text  # the edit actually landed
    regen = generate_ir_text(mutated)
    assert regen != REFERENCE_PATH.read_text()
    assert "s.score > 0.8 and not s.excluded" in regen
    assert check(loads(regen)) == []  # still a valid definition


def test_missing_cities_fails_loudly(english_text: str):
    """Dropping a required contract line fails instead of silently drifting."""
    lines = [
        ln for ln in english_text.splitlines() if not ln.strip().startswith("cities:")
    ]
    with pytest.raises(ValueError, match="missing required parameters"):
        generate_ir_text("\n".join(lines))


def test_prose_edits_dont_change_ir(english_text: str):
    """Rewording the human prose must never change the generated definition."""
    reworded = english_text.replace(
        "find the ones worth\nDavid's time: daily-pay roles he could actually take.",
        "surface the daily-pay roles actually worth David's morning.",
    )
    assert reworded != english_text  # the edit actually landed
    assert generate_ir_text(reworded) == REFERENCE_PATH.read_text()
