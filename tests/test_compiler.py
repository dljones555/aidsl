from __future__ import annotations

from aidsl.compiler import compile_program


def test_compile_generates_system_prompt(expense_program):
    plan = compile_program(expense_program)
    prompt = plan.extraction_prompt.system
    assert "merchant" in prompt
    assert "amount" in prompt
    assert "category" in prompt
    assert "travel" in prompt
    assert "meals" in prompt


def test_compile_prompt_constrains_money(expense_program):
    plan = compile_program(expense_program)
    prompt = plan.extraction_prompt.system
    assert "number" in prompt.lower() or "numeric" in prompt.lower()
    assert "$" in prompt or "dollar" in prompt.lower()


def test_compile_prompt_constrains_enum(expense_program):
    plan = compile_program(expense_program)
    prompt = plan.extraction_prompt.system
    assert "MUST be exactly one of" in prompt
    assert "travel" in prompt
    assert "equipment" in prompt


def test_compile_json_schema_properties(expense_program):
    plan = compile_program(expense_program)
    props = plan.extraction_prompt.json_schema["properties"]
    assert props["merchant"]["type"] == "string"
    assert props["amount"]["type"] == "number"
    assert props["category"]["type"] == "string"
    assert props["category"]["enum"] == [
        "travel",
        "meals",
        "equipment",
        "software",
        "office",
    ]


def test_compile_json_schema_required(expense_program):
    plan = compile_program(expense_program)
    required = plan.extraction_prompt.json_schema["required"]
    assert "merchant" in required
    assert "amount" in required
    assert "category" in required


def test_compile_flag_evaluator_created(expense_program):
    plan = compile_program(expense_program)
    assert len(plan.flag_evaluator.rules) == 2


def test_compile_schema_name(expense_program):
    plan = compile_program(expense_program)
    assert plan.schema.name == "expense"


def test_compile_source_and_output(expense_program):
    plan = compile_program(expense_program)
    assert plan.source == "receipts.csv"
    assert plan.output == "expenses.json"
