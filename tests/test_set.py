from __future__ import annotations

import textwrap

from aidsl.parser import Settings, parse
from aidsl.compiler import compile_program
from aidsl.runtime import _apply_settings


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_parse_set_model(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  a TEXT\n\nSET MODEL gpt-4.1\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.settings.model == "gpt-4.1"


def test_parse_set_temperature(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  a TEXT\n\nSET TEMPERATURE 0.3\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.settings.temperature == 0.3


def test_parse_set_top_p(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  a TEXT\n\nSET TOP_P 0.9\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.settings.top_p == 0.9


def test_parse_set_seed(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  a TEXT\n\nSET SEED 42\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.settings.seed == 42


def test_parse_set_multiple(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE x:
          a TEXT

        SET MODEL gpt-4.1
        SET TEMPERATURE 0.2
        SET SEED 99

        FROM d.csv
        EXTRACT x
        OUTPUT o.json
    """)
    )
    prog = parse(str(ai))
    assert prog.settings.model == "gpt-4.1"
    assert prog.settings.temperature == 0.2
    assert prog.settings.seed == 99


def test_parse_no_set_defaults(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a TEXT\n\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.settings.model == ""
    assert prog.settings.temperature is None
    assert prog.settings.top_p is None
    assert prog.settings.seed is None


# ---------------------------------------------------------------------------
# Compiler tests — settings passthrough
# ---------------------------------------------------------------------------


def test_compile_passes_settings(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE x:
          a TEXT

        SET MODEL gpt-4.1
        SET TEMPERATURE 0.5

        FROM d.csv
        EXTRACT x
        OUTPUT o.json
    """)
    )
    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))
    assert plan.settings.model == "gpt-4.1"
    assert plan.settings.temperature == 0.5


def test_compile_default_settings(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a TEXT\n\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n")
    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))
    assert plan.settings.model == ""
    assert plan.settings.temperature is None


# ---------------------------------------------------------------------------
# Runtime tests — _apply_settings
# ---------------------------------------------------------------------------


def test_apply_settings_temperature():
    body = {"model": "m", "messages": []}
    plan = _make_plan_with_settings(temperature=0.3)
    _apply_settings(body, plan)
    assert body["temperature"] == 0.3


def test_apply_settings_top_p():
    body = {"model": "m", "messages": []}
    plan = _make_plan_with_settings(top_p=0.9)
    _apply_settings(body, plan)
    assert body["top_p"] == 0.9


def test_apply_settings_seed():
    body = {"model": "m", "messages": []}
    plan = _make_plan_with_settings(seed=42)
    _apply_settings(body, plan)
    assert body["seed"] == 42


def test_apply_settings_none_skipped():
    body = {"model": "m", "messages": []}
    plan = _make_plan_with_settings()
    _apply_settings(body, plan)
    assert "temperature" not in body
    assert "top_p" not in body
    assert "seed" not in body


def test_apply_settings_all():
    body = {"model": "m", "messages": []}
    plan = _make_plan_with_settings(temperature=0.7, top_p=0.95, seed=123)
    _apply_settings(body, plan)
    assert body["temperature"] == 0.7
    assert body["top_p"] == 0.95
    assert body["seed"] == 123


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_plan_with_settings(**kwargs):
    from aidsl.compiler import ExecutionPlan, ExtractionPrompt, FlagEvaluator
    from aidsl.parser import Schema

    settings = Settings(**kwargs)
    return ExecutionPlan(
        source="d.csv",
        extraction_prompt=ExtractionPrompt(system="test", json_schema={}),
        flag_evaluator=FlagEvaluator(rules=[]),
        output="o.json",
        schema=Schema(name="x"),
        settings=settings,
    )
