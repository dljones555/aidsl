from __future__ import annotations

from unittest.mock import MagicMock, patch

from aidsl.parser import parse
from aidsl.compiler import compile_program
from aidsl.runtime import run
from tests.conftest import make_llm_response


def test_parse_classify_basic(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM d.csv\nCLASSIFY INTO [a, b, c]\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.classify is not None
    assert prog.classify.categories == ["a", "b", "c"]
    assert prog.classify.field_name == "classification"


def test_parse_classify_with_field_name(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM d.csv\nCLASSIFY type INTO [bug, feature, question]\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.classify.field_name == "type"
    assert prog.classify.categories == ["bug", "feature", "question"]


def test_parse_classify_with_flags(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM d.csv\nCLASSIFY type INTO [a, b]\nFLAG WHEN type IS b\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.classify is not None
    assert len(prog.flags) == 1


def test_compile_classify_prompt(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM d.csv\nCLASSIFY sentiment INTO [positive, negative, neutral]\nOUTPUT o.json\n")
    prog = parse(str(ai))
    plan = compile_program(prog)
    assert plan.verb == "CLASSIFY"
    assert "positive" in plan.extraction_prompt.system
    assert "negative" in plan.extraction_prompt.system
    assert "exactly one category" in plan.extraction_prompt.system.lower()


def test_compile_classify_json_schema(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM d.csv\nCLASSIFY type INTO [bug, feature]\nOUTPUT o.json\n")
    prog = parse(str(ai))
    plan = compile_program(prog)
    props = plan.extraction_prompt.json_schema["properties"]
    assert "type" in props
    assert props["type"]["enum"] == ["bug", "feature"]
    assert plan.extraction_prompt.json_schema["required"] == ["type"]


def test_compile_classify_synthetic_schema(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM d.csv\nCLASSIFY type INTO [a, b, c]\nOUTPUT o.json\n")
    prog = parse(str(ai))
    plan = compile_program(prog)
    assert plan.schema.name == "_classify"
    assert len(plan.schema.fields) == 1
    assert plan.schema.fields[0].name == "type"
    assert plan.schema.fields[0].enum_values == ["a", "b", "c"]


def _mock_post_factory(responses):
    call_count = 0

    def mock_post(url, headers=None, json=None):
        nonlocal call_count
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    return mock_post


def test_classify_runtime_pipeline(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM data.csv\nCLASSIFY type INTO [bug, feature, question]\nFLAG WHEN type IS bug\nOUTPUT out.json\n")

    csv = tmp_path / "data.csv"
    csv.write_text('text\n"App crashes on login"\n"Add dark mode please"\n')

    prog = parse(str(ai))
    plan = compile_program(prog)

    responses = [
        make_llm_response({"type": "bug"}),
        make_llm_response({"type": "feature"}),
    ]

    with patch("aidsl.runtime.os.environ.get") as mock_env, \
         patch("aidsl.runtime.httpx.Client") as mock_client_cls:
        mock_env.side_effect = lambda k, d="": "fake-token" if k == "GITHUB_TOKEN" else d
        mock_client = MagicMock()
        mock_client.post = _mock_post_factory(responses)
        mock_client_cls.return_value = mock_client

        results = run(plan, base_dir=str(tmp_path))

    assert len(results) == 2
    assert results[0]["type"] == "bug"
    assert results[0]["_flagged"] is True
    assert results[1]["type"] == "feature"
    assert results[1]["_flagged"] is False


def test_classify_rejects_invalid_category(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("FROM data.csv\nCLASSIFY type INTO [a, b]\nOUTPUT out.json\n")

    csv = tmp_path / "data.csv"
    csv.write_text('text\n"something"\n')

    prog = parse(str(ai))
    plan = compile_program(prog)

    responses = [make_llm_response({"type": "INVALID"})]

    with patch("aidsl.runtime.os.environ.get") as mock_env, \
         patch("aidsl.runtime.httpx.Client") as mock_client_cls:
        mock_env.side_effect = lambda k, d="": "fake-token" if k == "GITHUB_TOKEN" else d
        mock_client = MagicMock()
        mock_client.post = _mock_post_factory(responses)
        mock_client_cls.return_value = mock_client

        results = run(plan, base_dir=str(tmp_path))

    assert "_error" in results[0]
