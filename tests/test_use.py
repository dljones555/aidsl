from __future__ import annotations

from aidsl.parser import parse
from aidsl.compiler import compile_program


# --- Parser tests ---


def test_parse_extract_use(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a TEXT\n\nFROM d.csv\nEXTRACT x USE my_examples\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.extract_target == "x"
    assert prog.examples_name == "my_examples"


def test_parse_extract_with_and_use(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a TEXT\n\nFROM d.csv\nEXTRACT x WITH ctx USE ex\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.extract_target == "x"
    assert prog.prompt_name == "ctx"
    assert prog.examples_name == "ex"


def test_parse_classify_use(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM d.csv\nCLASSIFY type INTO [a, b, c] USE my_ex\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.classify is not None
    assert prog.examples_name == "my_ex"


def test_parse_classify_with_and_use(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM d.csv\nCLASSIFY type INTO [a, b] WITH ctx USE ex\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.prompt_name == "ctx"
    assert prog.examples_name == "ex"


def test_parse_standalone_use(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a TEXT\n\nFROM d.csv\nEXTRACT x\nUSE my_examples\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.examples_name == "my_examples"


def test_parse_no_use(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a TEXT\n\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.examples_name == ""


# --- Compiler tests ---


def test_compile_use_injects_examples(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  name TEXT\n\nFROM d.csv\nEXTRACT x USE test_ex\nOUTPUT o.json\n")

    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    (examples_dir / "test_ex.examples").write_text(
        "INPUT: John Smith invoice\n"
        'OUTPUT: {"name": "John Smith"}\n'
        "\n"
        "INPUT: Jane Doe receipt\n"
        'OUTPUT: {"name": "Jane Doe"}\n'
    )

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    assert "Example 1:" in plan.extraction_prompt.system
    assert "Example 2:" in plan.extraction_prompt.system
    assert "John Smith invoice" in plan.extraction_prompt.system
    assert "Jane Doe" in plan.extraction_prompt.system
    assert "Now process the following input" in plan.extraction_prompt.system


def test_compile_use_with_classify(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM d.csv\nCLASSIFY type INTO [a, b] USE cls_ex\nOUTPUT o.json\n")

    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    (examples_dir / "cls_ex.examples").write_text(
        "INPUT: something about topic a\n"
        'OUTPUT: {"type": "a"}\n'
    )

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    assert "Example 1:" in plan.extraction_prompt.system
    assert "something about topic a" in plan.extraction_prompt.system


def test_compile_with_and_use_together(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  name TEXT\n\nFROM d.csv\nEXTRACT x WITH ctx USE ex\nOUTPUT o.json\n")

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "ctx.prompt").write_text("You are a data processor.")

    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    (examples_dir / "ex.examples").write_text(
        "INPUT: test input\n"
        'OUTPUT: {"name": "test"}\n'
    )

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    # WITH context comes first
    assert plan.extraction_prompt.system.startswith("You are a data processor.")
    # USE examples are also present
    assert "Example 1:" in plan.extraction_prompt.system
    assert "test input" in plan.extraction_prompt.system


def test_compile_without_use_no_examples(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  name TEXT\n\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n")

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    assert "Example" not in plan.extraction_prompt.system


def test_compile_use_missing_file_raises(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  name TEXT\n\nFROM d.csv\nEXTRACT x USE nonexistent\nOUTPUT o.json\n")

    prog = parse(str(ai))

    try:
        compile_program(prog, base_dir=str(tmp_path))
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "nonexistent" in str(e)
        assert "examples/" in str(e)
