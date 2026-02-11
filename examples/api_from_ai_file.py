"""Python API example: load and run an existing .ai file.

Shows how to use the parser + compiler + runtime directly from Python,
giving you programmatic access to results without touching the CLI.

    cd examples && uv run python api_from_ai_file.py
"""

from __future__ import annotations

from aidsl.compiler import compile_program
from aidsl.parser import parse
from aidsl.runtime import run

# -- Parse the existing .ai file into a Program AST --
program = parse("triage_reply.ai")

# Inspect what the DSL defined
print(f"Source:   {program.source}")
print(f"Classify: {program.classify.field_name} -> {program.classify.categories}")
print(f"Draft:    {program.draft.field_name}")
print(f"Flags:    {len(program.flags)} rules")
print()

# -- Compile and run --
plan = compile_program(program, base_dir=".")
results = run(plan, base_dir=".")

# -- Post-process: filter to complaints only --
complaints = [r for r in results if r.get("type") == "complaint"]

print(f"\n--- Complaints ({len(complaints)}/{len(results)} tickets) ---")
for r in complaints:
    print(f"  Reply: {r.get('reply', '(no draft)')[:80]}...")
