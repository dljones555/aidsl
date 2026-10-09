"""Regeneration exam: the English spec is the source of truth.

PBI #38, story 4 (revised 2026-10-08). The honest chain, no invented layer:

    English -> .ai text -> parse (aidsl.parser) -> lower (ir.lower_program)
      -> check -> Spec -> .ir text

No Python objects cross the seam: the committed .ai file is deleted and
regenerated from the English spec, and only the real parser's output is
ever lowered. The .ir is the dumped Spec. They also prove the English is
load-bearing — a parameter change must change the .ai, while prose
rewording must not. There is no gate: the pipeline is a list.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from examples.gen_from_english import (
    generate_ai_text,
    generate_ir_text,
    load_ai,
    read_params,
)
from ir import check, dumps, loads

ENGLISH_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.english.md"
AI_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.ai"
IR_PATH = ROOT / "examples" / "ir" / "opportunity_pipeline.ir"


@pytest.fixture()
def english_text() -> str:
    """The committed English spec, as text."""
    return ENGLISH_PATH.read_text()


def _spec_from_ai_text(ai_text: str, tmp_path: Path):
    """Parse + lower .ai text through the real seam (temp file, since the
    .ai parser takes a path)."""
    p = tmp_path / "regen.ai"
    p.write_text(ai_text)
    return load_ai(p)


def test_ai_regeneration_matches_reference(english_text: str):
    """Regenerated .ai text is byte-identical to the committed file."""
    assert generate_ai_text(english_text) == AI_PATH.read_text()


def test_committed_ai_matches_regeneration(english_text: str, tmp_path: Path):
    """Delete-and-regenerate: the committed .ai is exactly what the
    English spec produces, and it parses, lowers, and checks clean."""
    ai_text = generate_ai_text(english_text)
    assert AI_PATH.read_text() == ai_text
    spec = _spec_from_ai_text(ai_text, tmp_path)
    assert spec.name == "opportunity_pipeline"


def test_ai_lowers_to_expected_shape(english_text: str, tmp_path: Path):
    """The real parser + real lowering produce the list pipeline: two ops,
    one plan, no gates, types and knowledge intact."""
    spec = _spec_from_ai_text(generate_ai_text(english_text), tmp_path)
    assert [p.name for p in spec.plans] == ["main"]
    assert [o.name for o in spec.ops] == ["extract_scored", "write_output"]
    assert {t.name for t in spec.types} == {"posting", "scored"}
    assert [k.name for k in spec.knowledge] == ["scored_source"]
    assert spec.gates == []
    extract = spec.ops[0]
    assert extract.using == "job_fit_v1"  # the prompt survived the chain


def test_lowered_spec_checks_clean(english_text: str, tmp_path: Path):
    """load_ai enforces the checker: violations fail loudly, never land."""
    spec = _spec_from_ai_text(generate_ai_text(english_text), tmp_path)
    assert check(spec) == []


def test_ir_regeneration_matches_reference(english_text: str):
    """The .ir is the dumped Spec: regenerated text matches the committed
    file byte-for-byte."""
    assert generate_ir_text(generate_ai_text(english_text)) == IR_PATH.read_text()


def test_ir_round_trips(english_text: str):
    """The dumped .ir re-parses to the identical text: stable artifact."""
    ir_text = generate_ir_text(generate_ai_text(english_text))
    assert dumps(loads(ir_text)) == ir_text


def test_mutated_threshold_changes_ai(english_text: str, tmp_path: Path):
    """Editing a declared parameter MUST change the generated .ai.

    The threshold rides with the prompt (comment in the .ai), so the
    artifact changes and still parses, lowers, and checks clean.
    """
    mutated = english_text.replace("score_threshold: 0.7", "score_threshold: 0.8")
    assert mutated != english_text  # the edit actually landed
    regen = generate_ai_text(mutated)
    assert regen != AI_PATH.read_text()
    assert "score_threshold 0.8" in regen
    spec = _spec_from_ai_text(regen, tmp_path)
    assert check(spec) == []


def test_missing_cities_fails_loudly(english_text: str):
    """Dropping a required contract line fails instead of silently drifting."""
    lines = [
        ln for ln in english_text.splitlines() if not ln.strip().startswith("cities:")
    ]
    with pytest.raises(ValueError, match="missing required parameters"):
        generate_ai_text("\n".join(lines))


def test_prose_edits_dont_change_ai(english_text: str):
    """Rewording the human prose must never change the generated definition."""
    reworded = english_text.replace(
        "score each one for fit, and\nshow the shortlist: the postings worth "
        "David's time.",
        "score each posting and show him the shortlist of fits.",
    )
    assert reworded != english_text  # the edit actually landed
    assert generate_ai_text(reworded) == AI_PATH.read_text()


def test_no_dsl_artifact_remains():
    """The .dsl was an unspecified invention: it must not come back."""
    assert not (ROOT / "examples" / "ir" / "opportunity_matcher.dsl").exists()


def test_threshold_param_is_a_number(english_text: str):
    """The contract's threshold parses as a float: the host filter and the
    eval read it from the same source of truth."""
    float(read_params(english_text)["score_threshold"])
