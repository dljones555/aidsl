"""Story 1 (PBI #38, revised 2026-10-08): the opportunity pipeline loads,
checks, and runs.

No gate: it's a list. CannedModel on a tiny inline fixture. The knowledge
entry is rebound to the fixture — bindings live outside the definition
(PBI #19). The FileModel/file path is covered by
examples/run_opportunity_scan.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from examples.gen_from_english import load_ai, read_params
from ir import CannedModel, Executor, ModelResult, check, render_card

ENGLISH_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.english.md"
AI_PATH = ROOT / "examples" / "ir" / "opportunity_matcher.ai"


def _tiny_fixture(tmp_path: Path) -> Path:
    """Two postings: one fit, one excluded. Minimal but exercises the
    shortlist filter."""
    postings = [
        {"id": "t1", "title": "Busser", "pay": "$17/hr", "employer": "M", "url": "u1"},
        {
            "id": "t2",
            "title": "Manager",
            "pay": "$95k/yr",
            "employer": "G",
            "url": "u2",
        },
    ]
    p = tmp_path / "tiny_postings.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in postings) + "\n")
    return p


def _threshold() -> float:
    """The shortlist cutoff's single source of truth: the English spec."""
    return float(read_params(ENGLISH_PATH.read_text())["score_threshold"])


def _run(tmp_path: Path):
    spec = load_ai(AI_PATH)
    assert check(spec) == []
    assert spec.gates == []  # no gate: a list
    # Rebind knowledge to the tiny fixture (PBI #19: bindings outside).
    spec.knowledge[0].uri = f"fs://{_tiny_fixture(tmp_path)}"
    scored = [
        ModelResult(
            {"id": "t1", "title": "Busser", "score": 0.8, "excluded": False}, 10, 5
        ),
        ModelResult(
            {"id": "t2", "title": "Manager", "score": 0.2, "excluded": True}, 10, 5
        ),
    ]
    model = CannedModel({"extract_scored": scored})
    # The sink fans out per scored item (general fanout semantic); the impl
    # accumulates, and the host applies the shortlist filter after the run.
    sunk: list = []

    def _write_output(item):
        sunk.append(item)
        return {"ok": True}

    executor = Executor(spec, model, op_impls={"write_output": _write_output})
    receipt = executor.run("main")
    threshold = _threshold()
    shortlist = [s for s in sunk if s["score"] > threshold and not s["excluded"]]
    captured = {"all": sunk, "shortlist": shortlist}
    return spec, receipt, captured


def test_pipeline_loads_checks_and_runs_to_list(tmp_path: Path):
    """End-to-end with CannedModel: completed, two steps, correct shortlist."""
    _spec, receipt, captured = _run(tmp_path)
    assert receipt.status == "completed"
    assert [s.var for s in receipt.steps] == ["raw", "out"]
    assert [s["title"] for s in captured["shortlist"]] == ["Busser"]
    assert len(captured["all"]) == 2  # every scoring recorded, not just fits
    assert receipt.audit_failures == []


def test_write_output_sinks_every_scoring(tmp_path: Path):
    """The sink sees every scored posting (one call per item); the
    shortlist filter is host policy applied after the run."""
    _spec, receipt, captured = _run(tmp_path)
    out_steps = [s for s in receipt.steps if s.op == "write_output"]
    assert len(out_steps) == 1  # one step; fanned per item inside
    assert len(captured["all"]) == 2
    assert captured["shortlist"] != []


def test_receipt_card_renders_for_run(tmp_path: Path):
    """render_card produces the user-presentable proof of the run."""
    _spec, receipt, _captured = _run(tmp_path)
    card = render_card(receipt)
    assert card.startswith("# Verify receipt — main")
    assert "extract_scored" in card
    assert "write_output" in card
