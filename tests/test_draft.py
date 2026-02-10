from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from aidsl.parser import parse
from aidsl.compiler import compile_program


# --- Parser tests ---


def test_parse_draft_with(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  name TEXT\n\n"
        "FROM d.csv\nEXTRACT x\nDRAFT summary WITH reply_tmpl\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.draft is not None
    assert prog.draft.field_name == "summary"
    assert prog.draft.prompt_name == "reply_tmpl"


def test_parse_draft_with_and_use(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  name TEXT\n\n"
        "FROM d.csv\nEXTRACT x\nDRAFT response WITH tmpl USE ex\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.draft.field_name == "response"
    assert prog.draft.prompt_name == "tmpl"
    assert prog.draft.examples_name == "ex"


def test_parse_draft_no_modifiers(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  name TEXT\n\n"
        "FROM d.csv\nEXTRACT x\nDRAFT summary\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.draft is not None
    assert prog.draft.field_name == "summary"
    assert prog.draft.prompt_name == ""


def test_parse_no_draft(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  name TEXT\n\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.draft is None


# --- Compiler tests ---


def test_compile_draft_prompt_created(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  name TEXT\n\n"
        "FROM d.csv\nEXTRACT x\nDRAFT summary WITH test_tmpl\nOUTPUT o.json\n"
    )

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "test_tmpl.prompt").write_text("Write a brief summary.")

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    assert plan.draft_prompt is not None
    assert plan.draft_prompt.field_name == "summary"
    assert "Write a brief summary." in plan.draft_prompt.system
    assert "structured data" in plan.draft_prompt.system.lower()


def test_compile_no_draft_prompt_when_absent(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  name TEXT\n\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n")

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    assert plan.draft_prompt is None


def test_compile_draft_with_classify(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "FROM d.csv\n"
        "CLASSIFY type INTO [a, b]\n"
        "DRAFT response WITH reply_tmpl\n"
        "OUTPUT o.json\n"
    )

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "reply_tmpl.prompt").write_text("Write a customer reply.")

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    assert plan.verb == "CLASSIFY"
    assert plan.draft_prompt is not None
    assert plan.draft_prompt.field_name == "response"


def test_compile_draft_missing_prompt_raises(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  name TEXT\n\n"
        "FROM d.csv\nEXTRACT x\nDRAFT summary WITH nonexistent\nOUTPUT o.json\n"
    )

    prog = parse(str(ai))
    try:
        compile_program(prog, base_dir=str(tmp_path))
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "nonexistent" in str(e)


# --- Runtime tests (mocked LLM) ---


def test_runtime_draft_appends_field(tmp_path):
    """Full pipeline: EXTRACT + DRAFT with mocked LLM."""
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  name TEXT\n\n"
        "FROM d.csv\nEXTRACT x\nDRAFT summary WITH tmpl\nOUTPUT o.json\n"
    )

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "tmpl.prompt").write_text("Summarize this record.")

    csv_file = tmp_path / "d.csv"
    csv_file.write_text('text\n"John Smith, consultant"\n')

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    # Mock the httpx responses: first for EXTRACT, second for DRAFT
    extract_resp = MagicMock()
    extract_resp.status_code = 200
    extract_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"name": "John Smith"})}}]
    }

    draft_resp = MagicMock()
    draft_resp.status_code = 200
    draft_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"summary": "Record for John Smith."})}}]
    }

    import os
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.side_effect = [extract_resp, draft_resp]
            mock_client_cls.return_value = mock_client

            from aidsl.runtime import run
            results = run(plan, base_dir=str(tmp_path))

    assert len(results) == 1
    assert results[0]["name"] == "John Smith"
    assert results[0]["summary"] == "Record for John Smith."
