"""First receipted run of the opportunity matcher (PBI #38, story 1, revised).

Loads examples/ir/opportunity_pipeline.ir, runs plan main with FileModel
(human-plays-model: model outputs come from a responses file, never the
network — $0). The postings come from the spec's own knowledge entry
(fs://), resolved by the executor. No gate: it's a list — the run scores
every posting, writes the shortlist, and renders a Markdown receipt card.

Usage:
    python3 examples/run_opportunity_scan.py [--responses PATH]
                                             [--out PATH] [--card PATH]

Run from the repo root so the knowledge fs:// path resolves.
--responses: pristine responses template (default:
    examples/ir/model_responses.jsonl). FileModel marks entries consumed
    by rewriting its file, so the script always works on a temp copy —
    the template is never mutated and runs are repeatable.
--out: where to write shortlist.json (default: examples/ir/shortlist.json).
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

from examples.gen_from_english import read_params
from ir import Executor, FileModel, ModelResult, check, loads, render_card

SPEC_PATH = ROOT / "examples" / "ir" / "opportunity_pipeline.ir"
ENGLISH_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.english.md"
RESPONSES_TEMPLATE = ROOT / "examples" / "ir" / "model_responses.jsonl"
DEFAULT_OUT = ROOT / "examples" / "ir" / "shortlist.json"


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
        "--responses",
        type=Path,
        default=RESPONSES_TEMPLATE,
        help="Pristine model-responses template (worked on via a temp copy).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Where to write shortlist.json.",
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
    threshold = float(read_params(ENGLISH_PATH.read_text())["score_threshold"])

    # FileModel consumes entries by rewriting its file: work on a temp
    # copy so the pristine template survives and runs stay repeatable.
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    shutil.copyfile(args.responses, tmp_path)
    try:
        model = RecordingModel(FileModel(tmp_path))
        # The sink fans out per scored item (general fanout semantic); the
        # impl accumulates, and the host writes the shortlist after the run.
        sunk: list[dict[str, Any]] = []

        def _write_output(item: Any) -> dict[str, Any]:
            sunk.append(item)
            return {"ok": True}

        executor = Executor(
            spec,
            model,
            op_impls={"write_output": _write_output},
        )
        receipt = executor.run("main")
    finally:
        tmp_path.unlink(missing_ok=True)

    shortlist = [s for s in sunk if s["score"] > threshold and not s["excluded"]]
    args.out.write_text(
        "\n".join(json.dumps(s) for s in shortlist) + "\n", encoding="utf-8"
    )

    scored = [data for op, data in model.seen if op == "extract_scored"]
    card = render_card(receipt, outputs={"scored": scored})

    print("Shortlist:")
    shortlist: list[dict[str, Any]] = []
    if args.out.exists():
        shortlist = [
            json.loads(line)
            for line in args.out.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    for s in shortlist:
        print(f"  - {s['title']} ({s['pay']}) score={s['score']}")
    print()
    if args.card:
        args.card.write_text(card, encoding="utf-8")
        print(f"receipt card written to {args.card}", file=sys.stderr)
    else:
        print(card, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
