from __future__ import annotations

import textwrap

import pytest

from aidsl.parser import parse
from aidsl.compiler import compile_program
from aidsl.runtime import _validate


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_parse_list_of_type(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE line_item:
          description TEXT
          quantity    NUMBER
          unit_price  MONEY

        DEFINE invoice:
          vendor TEXT
          items  LIST OF line_item

        FROM invoices/
        EXTRACT invoice
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    schema = prog.schemas["invoice"]
    items_field = schema.fields[1]
    assert items_field.name == "items"
    assert items_field.type == "LIST"
    assert items_field.ref_type == "line_item"


def test_parse_ref_type(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE address:
          street TEXT
          city   TEXT
          zip    TEXT

        DEFINE customer:
          name    TEXT
          billing address

        FROM data.csv
        EXTRACT customer
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    billing_field = prog.schemas["customer"].fields[1]
    assert billing_field.name == "billing"
    assert billing_field.type == "REF"
    assert billing_field.ref_type == "address"


def test_parse_list_of_preserves_child_schema(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE item:
          name  TEXT
          price MONEY

        DEFINE order:
          customer TEXT
          items    LIST OF item

        FROM data.csv
        EXTRACT order
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    # Child schema should still be parsed independently
    assert "item" in prog.schemas
    assert len(prog.schemas["item"].fields) == 2
    assert prog.schemas["item"].fields[0].name == "name"
    assert prog.schemas["item"].fields[1].name == "price"


# ---------------------------------------------------------------------------
# Compiler tests — JSON schema generation
# ---------------------------------------------------------------------------


def test_compile_list_of_json_schema(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE line_item:
          description TEXT
          quantity    NUMBER
          unit_price  MONEY

        DEFINE invoice:
          vendor TEXT
          total  MONEY
          items  LIST OF line_item

        FROM data.csv
        EXTRACT invoice
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))
    props = plan.extraction_prompt.json_schema["properties"]

    assert props["vendor"]["type"] == "string"
    assert props["total"]["type"] == "number"

    # items should be array of objects
    items = props["items"]
    assert items["type"] == "array"
    assert items["items"]["type"] == "object"
    item_props = items["items"]["properties"]
    assert item_props["description"]["type"] == "string"
    assert item_props["quantity"]["type"] == "number"
    assert item_props["unit_price"]["type"] == "number"
    assert items["items"]["required"] == ["description", "quantity", "unit_price"]


def test_compile_ref_json_schema(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE address:
          street TEXT
          city   TEXT
          zip    TEXT

        DEFINE customer:
          name    TEXT
          billing address

        FROM data.csv
        EXTRACT customer
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))
    props = plan.extraction_prompt.json_schema["properties"]

    assert props["name"]["type"] == "string"

    billing = props["billing"]
    assert billing["type"] == "object"
    assert billing["properties"]["street"]["type"] == "string"
    assert billing["properties"]["city"]["type"] == "string"
    assert billing["properties"]["zip"]["type"] == "string"
    assert billing["required"] == ["street", "city", "zip"]


def test_compile_missing_ref_raises(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE order:
          items LIST OF nonexistent

        FROM data.csv
        EXTRACT order
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    with pytest.raises(ValueError, match="Referenced type 'nonexistent' not defined"):
        compile_program(prog, base_dir=str(tmp_path))


def test_compile_missing_ref_type_raises(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE customer:
          name    TEXT
          billing no_such_type

        FROM data.csv
        EXTRACT customer
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    with pytest.raises(ValueError, match="Referenced type 'no_such_type' not defined"):
        compile_program(prog, base_dir=str(tmp_path))


def test_compile_prompt_describes_nested_fields(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE line_item:
          description TEXT
          amount      MONEY

        DEFINE invoice:
          vendor TEXT
          items  LIST OF line_item

        FROM data.csv
        EXTRACT invoice
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))
    prompt = plan.extraction_prompt.system
    assert "array of line_item" in prompt
    assert "description" in prompt
    assert "amount" in prompt


def test_compile_required_includes_nested_fields(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE item:
          name  TEXT
          price MONEY

        DEFINE order:
          customer TEXT
          items    LIST OF item

        FROM data.csv
        EXTRACT order
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))
    required = plan.extraction_prompt.json_schema["required"]
    assert "customer" in required
    assert "items" in required


# ---------------------------------------------------------------------------
# Validator tests — nested and array validation
# ---------------------------------------------------------------------------


def _make_invoice_plan(tmp_path):
    """Helper to build a plan with LIST OF for validator tests."""
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE line_item:
          description TEXT
          quantity    NUMBER
          unit_price  MONEY

        DEFINE invoice:
          vendor TEXT
          total  MONEY
          items  LIST OF line_item

        FROM data.csv
        EXTRACT invoice
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    return compile_program(prog, base_dir=str(tmp_path))


def test_validate_nested_list_valid(tmp_path):
    plan = _make_invoice_plan(tmp_path)
    record = {
        "vendor": "Acme",
        "total": 1500.00,
        "items": [
            {"description": "Widget", "quantity": 10, "unit_price": 100.00},
            {"description": "Gadget", "quantity": 5, "unit_price": 50.00},
        ],
    }
    assert _validate(record, plan) is True


def test_validate_nested_list_empty_array(tmp_path):
    plan = _make_invoice_plan(tmp_path)
    record = {
        "vendor": "Acme",
        "total": 0,
        "items": [],
    }
    assert _validate(record, plan) is True


def test_validate_nested_list_not_array(tmp_path):
    plan = _make_invoice_plan(tmp_path)
    record = {
        "vendor": "Acme",
        "total": 100,
        "items": "not a list",
    }
    assert _validate(record, plan) is False


def test_validate_nested_list_item_missing_field(tmp_path):
    plan = _make_invoice_plan(tmp_path)
    record = {
        "vendor": "Acme",
        "total": 100,
        "items": [
            {"description": "Widget", "quantity": 10},  # missing unit_price
        ],
    }
    assert _validate(record, plan) is False


def test_validate_nested_list_item_bad_number(tmp_path):
    plan = _make_invoice_plan(tmp_path)
    record = {
        "vendor": "Acme",
        "total": 100,
        "items": [
            {"description": "Widget", "quantity": "abc", "unit_price": 10.0},
        ],
    }
    assert _validate(record, plan) is False


def test_validate_nested_list_item_string_coercion(tmp_path):
    plan = _make_invoice_plan(tmp_path)
    record = {
        "vendor": "Acme",
        "total": 100,
        "items": [
            {"description": "Widget", "quantity": "10", "unit_price": "50.00"},
        ],
    }
    assert _validate(record, plan) is True
    assert record["items"][0]["quantity"] == 10.0
    assert record["items"][0]["unit_price"] == 50.0


def _make_ref_plan(tmp_path):
    """Helper to build a plan with REF type for validator tests."""
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE address:
          street TEXT
          city   TEXT

        DEFINE customer:
          name    TEXT
          billing address

        FROM data.csv
        EXTRACT customer
        OUTPUT out.json
    """)
    )
    prog = parse(str(ai))
    return compile_program(prog, base_dir=str(tmp_path))


def test_validate_ref_valid(tmp_path):
    plan = _make_ref_plan(tmp_path)
    record = {
        "name": "Alice",
        "billing": {"street": "123 Main", "city": "Springfield"},
    }
    assert _validate(record, plan) is True


def test_validate_ref_not_object(tmp_path):
    plan = _make_ref_plan(tmp_path)
    record = {
        "name": "Alice",
        "billing": "123 Main St",
    }
    assert _validate(record, plan) is False


def test_validate_ref_missing_nested_field(tmp_path):
    plan = _make_ref_plan(tmp_path)
    record = {
        "name": "Alice",
        "billing": {"street": "123 Main"},  # missing city
    }
    assert _validate(record, plan) is False


def test_validate_nested_list_item_not_dict(tmp_path):
    plan = _make_invoice_plan(tmp_path)
    record = {
        "vendor": "Acme",
        "total": 100,
        "items": ["not a dict"],
    }
    assert _validate(record, plan) is False


# ---------------------------------------------------------------------------
# End-to-end: parser → compiler → validate (no LLM)
# ---------------------------------------------------------------------------


def test_nested_list_full_pipeline(tmp_path):
    """Parse .ai with nested types, compile, and validate a mock LLM response."""
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE line_item:
          description TEXT
          quantity    NUMBER
          unit_price  MONEY

        DEFINE invoice:
          vendor      TEXT
          invoice_num TEXT
          total       MONEY
          items       LIST OF line_item

        FROM invoices/
        EXTRACT invoice
        FLAG WHEN total OVER 1000
        OUTPUT parsed_invoices.json
    """)
    )
    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    # Simulate a valid LLM response
    record = {
        "vendor": "Acme Corp",
        "invoice_num": "INV-001",
        "total": 1500.00,
        "items": [
            {"description": "Consulting", "quantity": 10, "unit_price": 100.00},
            {"description": "Support", "quantity": 5, "unit_price": 100.00},
        ],
    }
    assert _validate(record, plan) is True

    # Check flags work with nested schema
    flags = plan.flag_evaluator.evaluate(record)
    assert len(flags) == 1
    assert "OVER" in flags[0]


def test_ref_type_full_pipeline(tmp_path):
    """Parse .ai with type reference, compile, and validate."""
    ai = tmp_path / "t.ai"
    ai.write_text(
        textwrap.dedent("""\
        DEFINE address:
          street TEXT
          city   TEXT
          state  TEXT
          zip    TEXT

        DEFINE contact:
          name    TEXT
          email   TEXT
          address address

        FROM data.csv
        EXTRACT contact
        OUTPUT contacts.json
    """)
    )
    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    record = {
        "name": "Bob Smith",
        "email": "bob@example.com",
        "address": {
            "street": "456 Oak Ave",
            "city": "Portland",
            "state": "OR",
            "zip": "97201",
        },
    }
    assert _validate(record, plan) is True
