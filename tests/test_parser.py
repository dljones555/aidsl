from __future__ import annotations


from aidsl.parser import parse


def test_parse_define_text_field(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE thing:\n  name TEXT\n\nFROM x.csv\nEXTRACT thing\nOUTPUT out.json\n")
    prog = parse(str(ai))
    assert "thing" in prog.schemas
    assert prog.schemas["thing"].fields[0].name == "name"
    assert prog.schemas["thing"].fields[0].type == "TEXT"


def test_parse_define_money_field(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE item:\n  price MONEY\n\nFROM x.csv\nEXTRACT item\nOUTPUT out.json\n")
    prog = parse(str(ai))
    assert prog.schemas["item"].fields[0].type == "MONEY"


def test_parse_define_enum_field(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE item:\n  color ONE OF [red, blue, green]\n\nFROM x.csv\nEXTRACT item\nOUTPUT out.json\n")
    prog = parse(str(ai))
    f = prog.schemas["item"].fields[0]
    assert f.type == "ENUM"
    assert f.enum_values == ["red", "blue", "green"]


def test_parse_define_bool_field(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE item:\n  active YES/NO\n\nFROM x.csv\nEXTRACT item\nOUTPUT out.json\n")
    prog = parse(str(ai))
    assert prog.schemas["item"].fields[0].type == "BOOL"


def test_parse_define_number_field(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE item:\n  qty NUMBER\n\nFROM x.csv\nEXTRACT item\nOUTPUT out.json\n")
    prog = parse(str(ai))
    assert prog.schemas["item"].fields[0].type == "NUMBER"


def test_parse_from_extract_output(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a TEXT\n\nFROM data.csv\nEXTRACT x\nOUTPUT result.json\n")
    prog = parse(str(ai))
    assert prog.source == "data.csv"
    assert prog.extract_target == "x"
    assert prog.output == "result.json"


def test_parse_flag_over(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a MONEY\n\nFROM d.csv\nEXTRACT x\nFLAG WHEN a OVER 100\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert len(prog.flags) == 1
    assert prog.flags[0].conditions[0].field == "a"
    assert prog.flags[0].conditions[0].op == "OVER"
    assert prog.flags[0].conditions[0].value == "100"


def test_parse_flag_is(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  t TEXT\n\nFROM d.csv\nEXTRACT x\nFLAG WHEN t IS urgent\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.flags[0].conditions[0].op == "IS"
    assert prog.flags[0].conditions[0].value == "urgent"


def test_parse_flag_compound_and(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a MONEY\n  b TEXT\n\nFROM d.csv\nEXTRACT x\nFLAG WHEN b IS travel AND a OVER 200\nOUTPUT o.json\n")
    prog = parse(str(ai))
    rule = prog.flags[0]
    assert len(rule.conditions) == 2
    assert rule.conjunctions == ["AND"]


def test_parse_multiple_flags(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  a MONEY\n\nFROM d.csv\nEXTRACT x\nFLAG WHEN a OVER 500\nFLAG WHEN a UNDER 10\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert len(prog.flags) == 2


def test_parse_comments_ignored(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("-- comment\nDEFINE x:\n  a TEXT\n\n-- another\nFROM d.csv\nEXTRACT x\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert "x" in prog.schemas


def test_parse_full_expense(expense_program):
    prog = expense_program
    assert "expense" in prog.schemas
    schema = prog.schemas["expense"]
    assert len(schema.fields) == 3
    assert prog.source == "receipts.csv"
    assert prog.extract_target == "expense"
    assert len(prog.flags) == 2
    assert prog.output == "expenses.json"
