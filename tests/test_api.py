from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aidsl.api import Pipeline, SchemaBuilder
from aidsl.compiler import compile_program

from tests.conftest import make_llm_response


# ---------------------------------------------------------------------------
# SchemaBuilder tests
# ---------------------------------------------------------------------------


def test_schema_builder_basic_fields():
    schema = (
        SchemaBuilder("expense")
        .text("merchant")
        .money("amount")
        .number("quantity")
        .bool("approved")
        .enum("category", ["travel", "meals", "equipment"])
        .build()
    )
    assert schema.name == "expense"
    assert len(schema.fields) == 5
    assert schema.fields[0].name == "merchant"
    assert schema.fields[0].type == "TEXT"
    assert schema.fields[1].name == "amount"
    assert schema.fields[1].type == "MONEY"
    assert schema.fields[2].name == "quantity"
    assert schema.fields[2].type == "NUMBER"
    assert schema.fields[3].name == "approved"
    assert schema.fields[3].type == "BOOL"
    assert schema.fields[4].name == "category"
    assert schema.fields[4].type == "ENUM"
    assert schema.fields[4].enum_values == ["travel", "meals", "equipment"]


def test_schema_builder_nested_list_of():
    line_item = SchemaBuilder("line_item").text("desc").money("price").build()
    invoice = (
        SchemaBuilder("invoice")
        .text("vendor")
        .money("total")
        .list_of("items", line_item)
        .build()
    )
    assert invoice.fields[2].type == "LIST"
    assert invoice.fields[2].ref_type == "line_item"
    assert "line_item" in invoice._deps  # type: ignore[attr-defined]


def test_schema_builder_nested_ref():
    address = SchemaBuilder("address").text("city").text("state").build()
    person = SchemaBuilder("person").text("name").ref("home", address).build()
    assert person.fields[1].type == "REF"
    assert person.fields[1].ref_type == "address"
    assert "address" in person._deps  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Pipeline.to_program() tests
# ---------------------------------------------------------------------------


def test_pipeline_to_program_extract():
    schema = SchemaBuilder("expense").text("merchant").money("amount").build()
    program = (
        Pipeline()
        .source("receipts.csv")
        .extract(schema)
        .flag("amount OVER 500")
        .output("out.json")
        .to_program()
    )
    assert program.source == "receipts.csv"
    assert program.extract_target == "expense"
    assert program.output == "out.json"
    assert len(program.flags) == 1
    assert program.schemas["expense"] is schema


def test_pipeline_extract_classify_mutual_exclusion():
    schema = SchemaBuilder("item").text("name").build()
    p = Pipeline().extract(schema)
    with pytest.raises(ValueError, match="mutually exclusive"):
        p.classify("type", ["a", "b"])


def test_pipeline_classify_extract_mutual_exclusion():
    schema = SchemaBuilder("item").text("name").build()
    p = Pipeline().classify("type", ["a", "b"])
    with pytest.raises(ValueError, match="mutually exclusive"):
        p.extract(schema)


def test_pipeline_flag_parses_single_rule():
    program = Pipeline().flag("amount OVER 500").to_program()
    rule = program.flags[0]
    assert len(rule.conditions) == 1
    assert rule.conditions[0].field == "amount"
    assert rule.conditions[0].op == "OVER"
    assert rule.conditions[0].value == "500"


def test_pipeline_flag_parses_compound_rule():
    program = Pipeline().flag("category IS travel AND amount OVER 200").to_program()
    rule = program.flags[0]
    assert len(rule.conditions) == 2
    assert rule.conjunctions == ["AND"]


def test_pipeline_set_applies_settings():
    program = (
        Pipeline().set(model="gpt-4.1", temperature=0, top_p=0.9, seed=42).to_program()
    )
    assert program.settings.model == "gpt-4.1"
    assert program.settings.temperature == 0.0
    assert program.settings.top_p == 0.9
    assert program.settings.seed == 42


def test_pipeline_classify_builds_program():
    program = (
        Pipeline()
        .source("data.csv")
        .classify("sentiment", ["positive", "negative", "neutral"])
        .output("result.json")
        .to_program()
    )
    assert program.classify is not None
    assert program.classify.field_name == "sentiment"
    assert program.classify.categories == ["positive", "negative", "neutral"]
    assert program.extract_target == ""


def test_pipeline_draft_builds_program():
    schema = SchemaBuilder("item").text("name").money("price").build()
    program = (
        Pipeline()
        .source("data.csv")
        .extract(schema)
        .draft("summary")
        .output("result.json")
        .to_program()
    )
    assert program.draft is not None
    assert program.draft.field_name == "summary"


def test_pipeline_prompt_and_examples():
    schema = SchemaBuilder("item").text("name").build()
    program = (
        Pipeline().extract(schema).prompt("context").examples("samples").to_program()
    )
    assert program.prompt_name == "context"
    assert program.examples_name == "samples"


def test_pipeline_default_output():
    schema = SchemaBuilder("item").text("name").build()
    program = Pipeline().extract(schema).to_program()
    assert program.output == "output.json"


def test_pipeline_run_without_source_raises():
    schema = SchemaBuilder("item").text("name").build()
    p = Pipeline().extract(schema).output("out.json")
    with pytest.raises(ValueError, match="source"):
        p.run()


def test_nested_schema_round_trip():
    line_item = SchemaBuilder("line_item").text("desc").money("price").build()
    invoice = (
        SchemaBuilder("invoice").text("vendor").list_of("items", line_item).build()
    )
    program = Pipeline().extract(invoice).to_program()
    assert "line_item" in program.schemas
    assert "invoice" in program.schemas
    # Should compile without errors
    plan = compile_program(program)
    assert plan.schema.name == "invoice"


# ---------------------------------------------------------------------------
# run() and run_one() integration tests with mocked LLM
# ---------------------------------------------------------------------------


def _mock_post_factory(responses: list[dict]):
    call_count = 0

    def mock_post(url, headers=None, json=None):
        nonlocal call_count
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    return mock_post


def test_pipeline_run_end_to_end(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text('text\n"Coffee latte, $4.50"\n"Steak dinner, $45.00"\n')

    schema = (
        SchemaBuilder("item")
        .text("name")
        .money("price")
        .enum("type", ["food", "drink", "other"])
        .build()
    )

    responses = [
        make_llm_response({"name": "Starbucks", "price": 4.50, "type": "drink"}),
        make_llm_response({"name": "Outback", "price": 45.00, "type": "food"}),
    ]

    with (
        patch("aidsl.runtime.os.environ.get") as mock_env,
        patch("aidsl.runtime.httpx.Client") as mock_client_cls,
    ):
        mock_env.side_effect = lambda k, d="": (
            "fake-token" if k == "GITHUB_TOKEN" else d
        )
        mock_client = MagicMock()
        mock_client.post = _mock_post_factory(responses)
        mock_client_cls.return_value = mock_client

        results = (
            Pipeline()
            .source("data.csv")
            .extract(schema)
            .flag("price OVER 10")
            .output("result.json")
            .base_dir(str(tmp_path))
            .run()
        )

    assert len(results) == 2
    assert results[0]["_flagged"] is False
    assert results[1]["_flagged"] is True


def test_pipeline_run_one_with_mock(tmp_path):
    schema = (
        SchemaBuilder("expense")
        .text("merchant")
        .money("amount")
        .enum("category", ["travel", "meals", "equipment"])
        .build()
    )

    response = make_llm_response(
        {"merchant": "Delta", "amount": 1200, "category": "travel"}
    )

    with (
        patch("aidsl.api.os.environ.get") as mock_env,
        patch("aidsl.api.httpx.Client") as mock_client_cls,
    ):
        mock_env.side_effect = lambda k, d="": (
            "fake-token" if k == "GITHUB_TOKEN" else d
        )
        mock_client = MagicMock()
        mock_client.post = _mock_post_factory([response])
        mock_client_cls.return_value = mock_client

        result = (
            Pipeline()
            .extract(schema)
            .flag("amount OVER 500")
            .run_one('{"merchant": "Delta", "amount": 1200}')
        )

    assert result["merchant"] == "Delta"
    assert result["amount"] == 1200
    assert result["_flagged"] is True
    assert "amount OVER 500" in result["_flag_reasons"][0]
