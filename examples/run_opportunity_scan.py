"""First receipted run of the opportunity matcher (PBI #38, story 1).

Loads examples/ir/opportunity_pipeline.ir, feeds it the real
examples/ir/postings.jsonl, runs plan daily_scan with FileModel
(human-plays-model: model outputs come from a responses file, never the
network — $0), and renders a Markdown receipt card via
ir/receipt_card.render_card.

Usage:
    python3 examples/run_opportunity_scan.py [--verdict approve|reject|edit]
                                             [--responses PATH]
                                             [--card PATH]

--verdict: answer the approval gate. Omit it to suspend at the gate;
    the script prints how to resume. The reference executor is not
    checkpointed, so a resumed run re-executes from the top against a
    fresh copy of the responses file; runs are deterministic, so the
    re-execution reaches the same gate with the same drafts.
--responses: pristine responses template (default:
    examples/ir/model_responses.jsonl). FileModel marks entries consumed
    by rewriting its file, so the script always works on a temp copy —
    the template is never mutated and runs are repeatable.
--card: where to write the receipt card (default: stdout).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ir import (
    AutoVerdict,
    Executor,
    FileModel,
    ModelResult,
    SuspendAlways,
    check,
    loads,
    render_card,
)

SPEC_PATH = ROOT / "examples" / "ir" / "opportunity_pipeline.ir"
POSTINGS_PATH = ROOT / "examples" / "ir" / "postings.jsonl"
RESPONSES_TEMPLATE = ROOT / "examples" / "ir" / "model_responses.jsonl"


def load_postings(path: Path) -> list[dict[str, Any]]:
    """Read the knowledge input: one posting per JSONL line."""
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class RecordingModel:
    """FileModel wrapper that remembers each (op, data) for the card.

    The card's "what the model said" section shows real values when the
    host supplies them; this records them in call order so the script
    can hand them to render_card.
    """

    def __init__(self, inner: FileModel):
        self.inner = inner
        self.seen: list[tuple[str, Any]] = []

    def complete(self, *, op: str, prompt: str, schema: dict[str, Any]) -> ModelResult:
        """Delegate to FileModel and record the returned data."""
        result = self.inner.complete(op=op, prompt=prompt, schema=schema)
        self.seen.append((op, result.data))
        return result


def build_parser() -> argparse.ArgumentParser:
    """Define the script's command-line interface."""
    parser = argparse.ArgumentParser(
        description="Run the opportunity matcher IR end-to-end (FileModel, $0)."
    )
    parser.add_argument(
        "--verdict",
        choices=["approve", "edit", "reject"],
        default=None,
        help="Answer the approval gate. Omit to suspend at the gate.",
    )
    parser.add_argument(
        "--responses",
        type=Path,
        default=RESPONSES_TEMPLATE,
        help="Pristine model-responses template (worked on via a temp copy).",
    )
    parser.add_argument(
        "--card",
        type=Path,
        default=None,
        help="Write the receipt card here (default: stdout).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the pipeline and render the receipt card."""
    args = build_parser().parse_args(argv)

    spec = loads(SPEC_PATH.read_text(encoding="utf-8"))
    violations = check(spec)
    if violations:
        for v in violations:
            print(f"check {v.code}: {v.message}", file=sys.stderr)
        return 2

    # FileModel consumes entries by rewriting its file: work on a temp
    # copy so the pristine template survives and runs stay repeatable.
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    shutil.copyfile(args.responses, tmp_path)
    try:
        model = RecordingModel(FileModel(tmp_path))
        gate_io = AutoVerdict(args.verdict) if args.verdict else SuspendAlways()
        executor = Executor(
            spec,
            model,
            op_impls={"fetch_boards": lambda _inputs: load_postings(POSTINGS_PATH)},
            gate_io=gate_io,
        )
        receipt = executor.run("daily_scan")
    finally:
        tmp_path.unlink(missing_ok=True)

    outputs = {
        "s": [data for op, data in model.seen if op == "classify_posting"],
        "d": [data for op, data in model.seen if op == "draft_outreach"],
    }
    card = render_card(receipt, outputs=outputs)

    if receipt.status == "suspended":
        print(
            "Run suspended at the approval gate (no --verdict given).\n"
            "Resume with: python3 examples/run_opportunity_scan.py "
            "--verdict approve|edit|reject",
            file=sys.stderr,
        )
    if args.card:
        args.card.write_text(card, encoding="utf-8")
        print(f"receipt card written to {args.card}", file=sys.stderr)
    else:
        print(card, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
