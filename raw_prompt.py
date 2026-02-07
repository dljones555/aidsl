"""Comparison: raw prompt with NO schema constraints, NO validation.

Run this alongside the DSL to see the consistency difference.
Usage: uv run python raw_prompt.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from anthropic import Anthropic


def main():
    client = Anthropic()

    csv_path = Path("examples/receipts.csv")
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print("\n  === RAW PROMPT (no schema, no validation) ===\n")

    results = []
    for i, row in enumerate(rows):
        text = row.get("text", "")
        if not text:
            continue
        print(f"  [{i + 1}/{len(rows)}] {text[:55]}...")

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Extract the merchant, amount, and category "
                        f"from this receipt:\n{text}\n\nReturn JSON."
                    ),
                }
            ],
        )

        raw = response.content[0].text.strip()
        print(f"           -> {raw[:80]}")
        results.append({"input": text, "raw_output": raw})

    out = Path("examples/raw_output.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n  OUTPUT {len(results)} records -> {out}")
    print("  NOTE: Check raw_output.json for inconsistent keys, formats, categories\n")


if __name__ == "__main__":
    main()
