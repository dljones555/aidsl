"""Eval harness: does the IR pipeline match the known-good shortlist?

PBI #38, story 2 (revised 2026-10-08). Runs plan main from
examples/ir/opportunity_pipeline.ir over the fixture
examples/ir/eval_postings.jsonl with CannedModel (deterministic, $0, no
network). The canned scoring judgments come from each fixture line's
_judge field; the expected shortlist comes from _expect. The eval
compares the postings the pipeline shortlisted against the expected
shortlist, per posting, and exits non-zero on any mismatch.

What "match" means: exact shortlist equality — every expected-surface
posting is on the list AND no expected-skip posting is.

Scope honesty: today the canned judgments are fixed, so this eval
measures the pipeline machinery (knowledge seeding, fan-out, the
shortlist filter, ordering). When live model wiring lands, the same
fixture and expected shortlist will measure the model's judgments
instead — that is the point of the harness.

The shortlist filter (score > threshold, not excluded) is host
presentation policy; the threshold's single source of truth is the
English spec-params.

Usage:
    python3 examples/eval_opmatcher.py [--fixture PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from examples.gen_from_english import read_params
from ir import CannedModel, Executor, ModelResult, check, loads

SPEC_PATH = ROOT / "examples" / "ir" / "opportunity_pipeline.ir"
ENGLISH_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.english.md"
DEFAULT_FIXTURE = ROOT / "examples" / "ir" / "eval_postings.jsonl"


@dataclass
class PostingVerdict:
    """One posting: what the fixture expects vs what the pipeline did."""

    id: str
    title: str
    expected: bool  # True = should surface (on the list)
    actual: bool  # True = did surface
    why: str

    @property
    def ok(self) -> bool:
        """The pipeline agreed with the fixture on this posting."""
        return self.expected == self.actual


@dataclass
class EvalReport:
    """Per-posting verdicts plus the summary score."""

    verdicts: list[PostingVerdict] = field(default_factory=list)

    @property
    def correct(self) -> int:
        """Number of postings where pipeline and fixture agree."""
        return sum(1 for v in self.verdicts if v.ok)

    @property
    def total(self) -> int:
        """Number of postings evaluated."""
        return len(self.verdicts)

    @property
    def passed(self) -> bool:
        """Exact shortlist equality: every posting agreed."""
        return self.correct == self.total


def load_fixture(path: Path) -> list[dict[str, Any]]:
    """Read and validate the fixture: unique ids, judge and expect fields."""
    postings = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ids = [p["id"] for p in postings]
    if len(set(ids)) != len(ids):
        raise ValueError(f"fixture {path}: posting ids must be unique")
    for p in postings:
        judge = p.get("_judge", {})
        if not isinstance(judge.get("score"), (int, float)) or not isinstance(
            judge.get("excluded"), bool
        ):
            raise TypeError(
                f"fixture {path}: posting {p['id']} needs _judge.score (number) "
                "and _judge.excluded (bool)"
            )
        if p.get("_expect") not in ("surface", "skip"):
            raise ValueError(
                f"fixture {path}: posting {p['id']} needs _expect 'surface' or 'skip'"
            )
    return postings


def build_canned(postings: list[dict[str, Any]]) -> CannedModel:
    """CannedModel fed from the fixture's own _judge fields.

    Scoring responses carry each posting's id so the eval can trace
    which postings the pipeline shortlisted.
    """
    scored = [
        ModelResult(
            {
                "id": p["id"],
                "title": p["title"],
                "score": p["_judge"]["score"],
                "excluded": p["_judge"]["excluded"],
            },
            10,
            5,
        )
        for p in postings
    ]
    return CannedModel({"extract_scored": scored})


def run_eval(fixture_path: Path) -> EvalReport:
    """Run the pipeline over the fixture; compare shortlists posting by posting."""
    spec = loads(SPEC_PATH.read_text(encoding="utf-8"))
    violations = check(spec)
    if violations:
        raise ValueError(
            "spec fails check: "
            + "; ".join(f"{v.code} {v.message}" for v in violations)
        )
    # Rebind knowledge to the fixture: bindings live outside the definition.
    spec.knowledge[0].uri = f"fs://{fixture_path}"
    threshold = float(read_params(ENGLISH_PATH.read_text())["score_threshold"])
    postings = load_fixture(fixture_path)
    model = build_canned(postings)
    # The sink fans out per scored item (general fanout semantic); the impl
    # accumulates and the host applies the shortlist filter after the run.
    sunk: list[dict[str, Any]] = []

    def _write_output(item: Any) -> dict[str, Any]:
        sunk.append(item)
        return {"ok": True}

    executor = Executor(spec, model, op_impls={"write_output": _write_output})
    receipt = executor.run("main")
    assert receipt.status == "completed", f"eval run did not complete: {receipt.status}"

    surfaced = {s["id"] for s in sunk if s["score"] > threshold and not s["excluded"]}
    return EvalReport(
        [
            PostingVerdict(
                id=p["id"],
                title=p["title"],
                expected=p["_expect"] == "surface",
                actual=p["id"] in surfaced,
                why=p.get("_why", ""),
            )
            for p in postings
        ]
    )


def format_report(report: EvalReport) -> str:
    """Human-readable per-posting lines plus the summary score."""
    lines = []
    for v in report.verdicts:
        mark = "PASS" if v.ok else "FAIL"
        want = "surface" if v.expected else "skip"
        got = "surfaced" if v.actual else "skipped"
        lines.append(f"[{mark}] {v.id} {v.title}: expected {want}, {got} — {v.why}")
    lines.append(f"{report.correct}/{report.total} correct")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Define the eval's command-line interface."""
    parser = argparse.ArgumentParser(
        description="Eval: does the IR pipeline match the known-good shortlist?"
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Fixture JSONL (default: examples/ir/eval_postings.jsonl).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the eval; exit 0 on exact shortlist equality, 1 otherwise."""
    args = build_parser().parse_args(argv)
    report = run_eval(args.fixture)
    print(format_report(report), end="")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
