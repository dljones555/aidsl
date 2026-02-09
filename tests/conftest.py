from __future__ import annotations

import json
import textwrap

import pytest

from aidsl.parser import parse, Program
from aidsl.compiler import compile_program, ExecutionPlan


@pytest.fixture()
def expense_ai(tmp_path):
    """Write a standard expense.ai file and return its path."""
    ai_file = tmp_path / "expense.ai"
    ai_file.write_text(textwrap.dedent("""\
        DEFINE expense:
          merchant    TEXT
          amount      MONEY
          category    ONE OF [travel, meals, equipment, software, office]

        FROM receipts.csv
        EXTRACT expense
        FLAG WHEN amount OVER 500
        FLAG WHEN category IS travel AND amount OVER 200
        OUTPUT expenses.json
    """))
    return ai_file


@pytest.fixture()
def expense_program(expense_ai) -> Program:
    """Parse the standard expense.ai into a Program."""
    return parse(str(expense_ai))


@pytest.fixture()
def expense_plan(expense_program) -> ExecutionPlan:
    """Compile the standard expense program into an ExecutionPlan."""
    return compile_program(expense_program)


@pytest.fixture()
def sample_csv(tmp_path):
    """Write a sample receipts.csv and return its parent dir."""
    csv_file = tmp_path / "receipts.csv"
    csv_file.write_text(
        'text\n'
        '"Uber ride to airport, $47.50"\n'
        '"MacBook Pro from Apple Store, $2499.00"\n'
        '"Hotel at Marriott, 3 nights, $687.00"\n'
    )
    return tmp_path


def make_llm_response(record: dict) -> dict:
    """Build a fake GitHub Models API response body."""
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(record),
                    "role": "assistant",
                }
            }
        ]
    }
