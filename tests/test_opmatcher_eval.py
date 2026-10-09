"""Story 2 (PBI #38, revised): the eval harness measures the pipeline, not itself.

The fixture carries known-good answers; the eval must pass on it, fail on
a corrupted copy. No gate, no drafts: the shortlist is the observable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "examples"))

from eval_opmatcher import (
    DEFAULT_FIXTURE,
    format_report,
    load_fixture,
    main,
    run_eval,
)


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


def test_eval_rejects_fixture_without_judge(tmp_path):
    """A fixture line missing its judge fields fails loudly, not silently."""
    bad = tmp_path / "njudge.jsonl"
    bad.write_text(json.dumps({"id": "x1", "title": "T"}) + "\n", encoding="utf-8")
    with pytest.raises(TypeError, match="_judge.score"):
        load_fixture(bad)


def test_eval_report_formats(tmp_path):
    """The human-readable report carries per-posting verdicts and a score."""
    report = run_eval(DEFAULT_FIXTURE)
    text = format_report(report)
    assert "10/10 correct" in text
    assert "[PASS]" in text


def test_eval_main_exit_codes(tmp_path):
    """main() exits 0 on pass, 1 on a corrupted fixture."""
    assert main(["--fixture", str(DEFAULT_FIXTURE)]) == 0
    lines = DEFAULT_FIXTURE.read_text(encoding="utf-8").splitlines()
    posting = json.loads(lines[0])
    posting["_expect"] = "skip"
    lines[0] = json.dumps(posting)
    bad_fixture = tmp_path / "bad.jsonl"
    bad_fixture.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert main(["--fixture", str(bad_fixture)]) == 1
