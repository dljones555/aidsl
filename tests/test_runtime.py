from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from aidsl.parser import parse
from aidsl.compiler import compile_program
from aidsl.runtime import run

from tests.conftest import make_llm_response


def _mock_post_factory(responses: list[dict]):
    """Return a side_effect function that returns mock responses in order."""
    call_count = 0

    def mock_post(url, headers=None, json=None):
        nonlocal call_count
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    return mock_post


def test_runtime_full_pipeline(tmp_path):
    # Write .ai file
    ai_file = tmp_path / "test.ai"
    ai_file.write_text(
        "DEFINE item:\n"
        "  name TEXT\n"
        "  price MONEY\n"
        "  type ONE OF [food, drink, other]\n"
        "\n"
        "FROM data.csv\n"
        "EXTRACT item\n"
        "FLAG WHEN price OVER 10\n"
        "OUTPUT result.json\n"
    )

    # Write CSV
    csv_file = tmp_path / "data.csv"
    csv_file.write_text('text\n"Coffee latte, $4.50"\n"Steak dinner, $45.00"\n')

    # Parse and compile
    program = parse(str(ai_file))
    plan = compile_program(program)

    # Mock LLM responses
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

        results = run(plan, base_dir=str(tmp_path))

    assert len(results) == 2

    # First record: coffee, not flagged
    assert results[0]["name"] == "Starbucks"
    assert results[0]["price"] == 4.50
    assert results[0]["_flagged"] is False

    # Second record: steak, flagged
    assert results[1]["name"] == "Outback"
    assert results[1]["price"] == 45.00
    assert results[1]["_flagged"] is True
    assert "price OVER 10" in results[1]["_flag_reasons"][0]

    # Output file written
    output = json.loads((tmp_path / "result.json").read_text())
    assert len(output) == 2


def test_runtime_invalid_llm_response_fails(tmp_path):
    ai_file = tmp_path / "test.ai"
    ai_file.write_text(
        "DEFINE item:\n"
        "  name TEXT\n"
        "  type ONE OF [a, b]\n"
        "\n"
        "FROM data.csv\n"
        "EXTRACT item\n"
        "OUTPUT result.json\n"
    )

    csv_file = tmp_path / "data.csv"
    csv_file.write_text('text\n"something"\n')

    program = parse(str(ai_file))
    plan = compile_program(program)

    # LLM returns invalid enum value every time
    bad_response = make_llm_response({"name": "X", "type": "INVALID"})

    with (
        patch("aidsl.runtime.os.environ.get") as mock_env,
        patch("aidsl.runtime.httpx.Client") as mock_client_cls,
    ):
        mock_env.side_effect = lambda k, d="": (
            "fake-token" if k == "GITHUB_TOKEN" else d
        )
        mock_client = MagicMock()
        mock_client.post = _mock_post_factory([bad_response])
        mock_client_cls.return_value = mock_client

        results = run(plan, base_dir=str(tmp_path))

    assert len(results) == 1
    assert "_error" in results[0]


def test_runtime_markdown_fences_stripped(tmp_path):
    ai_file = tmp_path / "test.ai"
    ai_file.write_text(
        "DEFINE item:\n  name TEXT\n\nFROM data.csv\nEXTRACT item\nOUTPUT result.json\n"
    )

    csv_file = tmp_path / "data.csv"
    csv_file.write_text('text\n"something"\n')

    program = parse(str(ai_file))
    plan = compile_program(program)

    # LLM wraps response in markdown fences
    fenced = {
        "choices": [
            {
                "message": {
                    "content": '```json\n{"name": "Test"}\n```',
                    "role": "assistant",
                }
            }
        ]
    }

    with (
        patch("aidsl.runtime.os.environ.get") as mock_env,
        patch("aidsl.runtime.httpx.Client") as mock_client_cls,
    ):
        mock_env.side_effect = lambda k, d="": (
            "fake-token" if k == "GITHUB_TOKEN" else d
        )
        mock_client = MagicMock()
        mock_client.post = _mock_post_factory([fenced])
        mock_client_cls.return_value = mock_client

        results = run(plan, base_dir=str(tmp_path))

    assert results[0]["name"] == "Test"
