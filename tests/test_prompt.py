from __future__ import annotations

from aidsl.parser import parse
from aidsl.compiler import compile_program


def test_parse_extract_prompt(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  a TEXT\n\nFROM d.csv\nEXTRACT x PROMPT my_context\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.extract_target == "x"
    assert prog.prompt_name == "my_context"


def test_parse_classify_prompt(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "FROM d.csv\nCLASSIFY type INTO [a, b, c]\n  PROMPT my_context\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.classify is not None
    assert prog.prompt_name == "my_context"


def test_parse_standalone_prompt(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  a TEXT\n\nFROM d.csv\nEXTRACT x\nPROMPT my_context\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.prompt_name == "my_context"


def test_parse_no_prompt(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a TEXT\n\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.prompt_name == ""


def test_compile_prompt_prepends_context(tmp_path):
    # Create .ai file
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  name TEXT\n\nFROM d.csv\nEXTRACT x PROMPT test_prompt\nOUTPUT o.json\n"
    )

    # Create prompts/test_prompt.prompt
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "test_prompt.prompt").write_text(
        "You are a helpful data processor.\nBe precise."
    )

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    # The context should appear at the start of the system prompt
    assert plan.extraction_prompt.system.startswith("You are a helpful data processor.")
    # The extraction instructions should still be there
    assert "Extract the following fields" in plan.extraction_prompt.system


def test_compile_classify_prompt_prepends_context(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "FROM d.csv\nCLASSIFY type INTO [a, b]\n  PROMPT my_ctx\nOUTPUT o.json\n"
    )

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "my_ctx.prompt").write_text("You are an expert classifier.")

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    assert plan.extraction_prompt.system.startswith("You are an expert classifier.")
    assert "exactly one category" in plan.extraction_prompt.system.lower()


def test_compile_without_prompt_no_context(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  name TEXT\n\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n")

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    # Should start directly with extraction instructions
    assert plan.extraction_prompt.system.startswith("Extract the following fields")


def test_compile_prompt_missing_file_raises(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  name TEXT\n\nFROM d.csv\nEXTRACT x PROMPT nonexistent\nOUTPUT o.json\n"
    )

    prog = parse(str(ai))

    try:
        compile_program(prog, base_dir=str(tmp_path))
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "nonexistent" in str(e)
        assert "prompts/" in str(e)
