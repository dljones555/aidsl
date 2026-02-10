from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from aidsl.parser import parse
from aidsl.compiler import compile_program
from aidsl.runtime import _substitute_placeholders


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
    assert "_draft_prompt" in results[0]


# --- DRAFT v2: placeholder substitution tests ---


def test_substitute_basic():
    template = "This is a {type} ticket from {name}."
    record = {"type": "complaint", "name": "Jane"}
    result = _substitute_placeholders(template, record)
    assert result == "This is a complaint ticket from Jane."


def test_substitute_multiple_same_field():
    template = "Type: {type}. Again: {type}."
    record = {"type": "claim"}
    result = _substitute_placeholders(template, record)
    assert result == "Type: claim. Again: claim."


def test_substitute_unknown_placeholder_left():
    template = "Hello {name}, your {unknown_field} is ready."
    record = {"name": "Bob"}
    result = _substitute_placeholders(template, record)
    assert result == "Hello Bob, your {unknown_field} is ready."


def test_substitute_skips_internal_fields():
    template = "Name: {name}, source: {_source}."
    record = {"name": "Alice", "_source": "raw text"}
    result = _substitute_placeholders(template, record)
    assert result == "Name: Alice, source: {_source}."


def test_substitute_numeric_values():
    template = "Amount is {amount} dollars."
    record = {"amount": 47.50}
    result = _substitute_placeholders(template, record)
    assert result == "Amount is 47.5 dollars."


def test_substitute_no_placeholders():
    template = "Write a summary of the record."
    record = {"name": "Test"}
    result = _substitute_placeholders(template, record)
    assert result == "Write a summary of the record."


def test_runtime_draft_substitutes_placeholders(tmp_path):
    """Full pipeline: CLASSIFY + DRAFT with {field} placeholders in template."""
    ai = tmp_path / "t.ai"
    ai.write_text(
        "FROM d.csv\n"
        "CLASSIFY type INTO [claim, inquiry]\n"
        "DRAFT response WITH tmpl\n"
        "OUTPUT o.json\n"
    )

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "tmpl.prompt").write_text(
        "This is a {type} ticket. Write a helpful reply."
    )

    csv_file = tmp_path / "d.csv"
    csv_file.write_text('text\n"I need to file a claim"\n')

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    # Verify the template has the raw placeholder
    assert "{type}" in plan.draft_prompt.system

    # Mock LLM: first call = classify, second call = draft
    classify_resp = MagicMock()
    classify_resp.status_code = 200
    classify_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"type": "claim"})}}]
    }

    draft_resp = MagicMock()
    draft_resp.status_code = 200
    draft_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"response": "Your claim has been received."})}}]
    }

    import os
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.side_effect = [classify_resp, draft_resp]
            mock_client_cls.return_value = mock_client

            from aidsl.runtime import run
            results = run(plan, base_dir=str(tmp_path))

    assert len(results) == 1
    assert results[0]["type"] == "claim"
    assert results[0]["response"] == "Your claim has been received."

    # Verify resolved prompt is in the output for audit
    assert "_draft_prompt" in results[0]
    assert "This is a claim ticket" in results[0]["_draft_prompt"]
    assert "{type}" not in results[0]["_draft_prompt"]

    # Verify the second LLM call got the substituted prompt (not raw {type})
    draft_call = mock_client.post.call_args_list[1]
    draft_body = draft_call[1]["json"]
    system_msg = draft_body["messages"][0]["content"]
    assert "This is a claim ticket" in system_msg
    assert "{type}" not in system_msg
