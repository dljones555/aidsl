"""Story 2 (PBI #38): the eval harness measures the pipeline, not itself.

The fixture carries known-good answers; the eval must pass on it, fail on
a corrupted copy, and the fixture's own _expect annotations must agree
with the spec's when-expression applied to the _judge values.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "examples"))

from eval_opmatcher import (
    DEFAULT_FIXTURE,
    format_report,
    load_fixture,
    main,
    run_eval,
)

from ir import evaluate, loads


def _draft_step_when() -> tuple[str, str]:
    """The (arg name, when expression) of the pipeline's draft step."""
    spec = loads((ROOT / "examples" / "ir" / "opportunity_pipeline.ir").read_text())
    step = next(s for s in spec.plans[0].steps if s.op == "draft_outreach")
    assert step.when, "draft step must carry the shortlist filter"
    return step.args[0], step.when


def test_eval_passes_on_committed_fixture():
    """The pipeline reproduces the known-good shortlist: 10/10."""
    report = run_eval(DEFAULT_FIXTURE)
    assert report.total == 10
    assert report.passed
    assert report.correct == 10


def test_eval_fails_on_wrong_expected_shortlist(tmp_path):
    """Flipping one expectation must fail: the eval actually discriminates."""
    lines = DEFAULT_FIXTURE.read_text(encoding="utf-8").splitlines()
    corrupted = []
    for line in lines:
        posting = json.loads(line)
        if posting["id"] == "p01":  # a clear match, corrupted to "skip"
            posting["_expect"] = "skip"
        corrupted.append(json.dumps(posting))
    bad_fixture = tmp_path / "bad_postings.jsonl"
    bad_fixture.write_text("\n".join(corrupted) + "\n", encoding="utf-8")

    report = run_eval(bad_fixture)
    assert not report.passed
    assert report.correct == 9
    p01 = next(v for v in report.verdicts if v.id == "p01")
    assert not p01.ok


def test_eval_main_exits_nonzero_on_mismatch(tmp_path, capsys):
    """The CLI is CI-usable: exit 1 and a FAIL line on any mismatch."""
    lines = DEFAULT_FIXTURE.read_text(encoding="utf-8").splitlines()
    posting = json.loads(lines[4])  # p05, a clear match
    posting["_expect"] = "skip"
    lines[4] = json.dumps(posting)
    bad_fixture = tmp_path / "bad_postings.jsonl"
    bad_fixture.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert main(["--fixture", str(bad_fixture)]) == 1
    out = capsys.readouterr().out
    assert "[FAIL] p05" in out
    assert "9/10 correct" in out


def test_fixture_expectations_agree_with_spec_when_rule():
    """The fixture's _expect annotations match its _judge values under the
    spec's real when-expression — guards against a misbuilt fixture."""
    arg, when = _draft_step_when()
    for p in load_fixture(DEFAULT_FIXTURE):
        decided = bool(evaluate(when, {arg: p["_judge"]}))
        assert decided == (p["_expect"] == "surface"), (
            f"fixture posting {p['id']}: _expect={p['_expect']} disagrees "
            f"with _judge={p['_judge']} under when={when!r}"
        )


def test_fixture_rejects_bad_input(tmp_path):
    """Duplicate ids and missing _expect fail loudly, not silently."""
    dup = tmp_path / "dup.jsonl"
    line = json.dumps(
        {
            "id": "p01",
            "title": "x",
            "_judge": {"score": 0.9, "excluded": False},
            "_expect": "surface",
        }
    )
    dup.write_text(line + "\n" + line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_fixture(dup)

    bad_expect = tmp_path / "bad_expect.jsonl"
    bad_expect.write_text(
        json.dumps(
            {
                "id": "p01",
                "title": "x",
                "_judge": {"score": 0.9, "excluded": False},
                "_expect": "maybe",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="_expect"):
        load_fixture(bad_expect)


def test_report_format_is_stable():
    """The report renders one line per posting plus the summary score."""
    report = run_eval(DEFAULT_FIXTURE)
    text = format_report(report)
    assert text.count("[PASS]") == 10
    assert text.rstrip().endswith("10/10 correct")
