"""Python API example: expense processing from scratch.

Equivalent to expense.ai but built entirely with the fluent Python API.
Uses the same receipts.csv input file.

    cd examples && uv run python api_expense.py
"""

from __future__ import annotations

from aidsl import Pipeline, SchemaBuilder

# -- Define schema (same fields as expense.ai DEFINE block) --
expense = (
    SchemaBuilder("expense")
    .text("merchant")
    .money("amount")
    .enum("category", ["travel", "meals", "equipment", "software", "office"])
    .build()
)

# -- Build and run the pipeline --
results = (
    Pipeline()
    .source("receipts.csv")
    .extract(expense)
    .use_examples("expense_samples")
    .flag("amount OVER 500")
    .flag("category IS travel AND amount OVER 200")
    .set(model="gpt-4.1", temperature=0, seed=42)
    .output("expenses_api.json")
    .run()
)

# -- Print summary --
for r in results:
    flag = " ** FLAGGED" if r.get("_flagged") else ""
    print(f"  {r.get('merchant', '?'):20s}  ${r.get('amount', 0):>8.2f}  {r.get('category', '?')}{flag}")
